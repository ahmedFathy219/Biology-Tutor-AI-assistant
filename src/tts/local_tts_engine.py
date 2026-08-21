import re
import tempfile
import os
import threading
import pygame
import wave
import numpy as np
from piper import PiperVoice, SynthesisConfig
import requests

config = SynthesisConfig(
    length_scale=1.2,   # slower (default 1.0)
    noise_scale=0.8,    # more variation (default ~0.667)
    volume=1.1          # louder (default 1.0)
)


class LocalTTSEngine:
    def __init__(self, voice_model=None, pause_event=None, resume_event=None):
        """
        Initialise local TTS with Piper.
        :param voice_model: path to .onnx voice model (optional). If None, uses a default.
        """
        pygame.mixer.init()
        self.pause_event = pause_event
        self.resume_event = resume_event

        self.is_speaking = False
        self.is_paused = False
        self.stop_requested = False
        self.stop_pending = False
        self._generation = 0
        self._lock = threading.Lock()

        # Load Piper voice
        self.voice = self._load_voice(voice_model)
        self.default_length_scale = 1.0
        self.default_noise_scale = 0.667

    def _load_voice(self, model_path):
        if model_path is None:
            model_path = self._download_default_model()
        return PiperVoice.load(model_path)

    def _download_default_model(self):
        """Download en_GB-alan-medium (ONNX + JSON) with validation."""
        home = os.path.expanduser("~")
        cache_dir = os.path.join(home, ".piper_voices")
        os.makedirs(cache_dir, exist_ok=True)

        # Use David Attenborough‑like voice: en_GB-alan-medium
        model_name = "en_GB-alan-medium"
        base_url = "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/alan/medium"

        model_file = os.path.join(cache_dir, f"{model_name}.onnx")
        json_file = os.path.join(cache_dir, f"{model_name}.onnx.json")

        MIN_ONNX_SIZE = 10 * 1024 * 1024  # 10 MB
        MIN_JSON_SIZE = 100               # bytes

        def download_file(url, dest_path, min_size):
            print(f"[LocalTTS] Downloading {url} -> {dest_path}")
            try:
                r = requests.get(url, stream=True, timeout=30)
                r.raise_for_status()
                total_size = int(r.headers.get('content-length', 0))
                with open(dest_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                actual_size = os.path.getsize(dest_path)
                if total_size > 0 and actual_size != total_size:
                    raise RuntimeError(f"Size mismatch: expected {total_size}, got {actual_size}")
                if actual_size < min_size:
                    raise RuntimeError(f"File too small: {actual_size} bytes (min {min_size})")
                print(f"[LocalTTS] Downloaded {actual_size} bytes")
            except Exception as e:
                if os.path.exists(dest_path):
                    os.remove(dest_path)
                raise RuntimeError(f"Failed to download {url}: {e}")

        if not os.path.exists(model_file) or os.path.getsize(model_file) < MIN_ONNX_SIZE:
            if os.path.exists(model_file):
                os.remove(model_file)
            download_file(f"{base_url}/{model_name}.onnx", model_file, MIN_ONNX_SIZE)

        if not os.path.exists(json_file) or os.path.getsize(json_file) < MIN_JSON_SIZE:
            if os.path.exists(json_file):
                os.remove(json_file)
            download_file(f"{base_url}/{model_name}.onnx.json", json_file, MIN_JSON_SIZE)

        return model_file

    def clean_text(self, text: str) -> str:
        text = re.sub(r"[*_`#]", "", text)
        text = text.replace("- ", ". ")
        text = text.replace("• ", ". ")
        text = re.sub(r"\d+\.\s*", "", text)
        text = text.replace("\n", ". ")
        text = re.sub(r"\s+", " ", text)
        return text.strip()
    
    def _adjust_parameters(self, text: str):
        """Tone parameters (currently not used because older Piper versions don't accept them)."""
        return 1.0, 0.667

    def _play_audio(self, audio_bytes, generation, sample_rate=None):
        temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        temp_path = temp_file.name
        try:
            if sample_rate is None:
                # Assume audio_bytes is a complete WAV file
                temp_file.write(audio_bytes)
                temp_file.close()
            else:
                # Write raw PCM with WAV header
                temp_file.close()
                with wave.open(temp_path, 'wb') as wav_file:
                    wav_file.setnchannels(1)
                    wav_file.setsampwidth(2)
                    wav_file.setframerate(sample_rate)
                    wav_file.writeframes(audio_bytes)

            with self._lock:
                if generation != self._generation or self.stop_requested:
                    return False

            pygame.mixer.music.load(temp_path)

            with self._lock:
                if self.stop_requested:
                    return False
            pygame.mixer.music.play()

            clock = pygame.time.Clock()
            while True:
                with self._lock:
                    stop_requested = self.stop_requested
                    is_paused = self.is_paused

                if self.pause_event and self.pause_event.is_set():
                    if not is_paused:
                        pygame.mixer.music.pause()
                        with self._lock:
                            self.is_paused = True
                    self.pause_event.clear()
                    is_paused = True

                if self.resume_event and self.resume_event.is_set():
                    if is_paused:
                        pygame.mixer.music.unpause()
                        with self._lock:
                            self.is_paused = False
                    self.resume_event.clear()
                    is_paused = False

                if stop_requested:
                    pygame.mixer.music.stop()
                    return False

                if is_paused:
                    clock.tick(20)
                    continue

                if not pygame.mixer.music.get_busy():
                    break

                clock.tick(50)
            return True

        finally:
            pygame.mixer.music.stop()
            try:
                pygame.mixer.music.unload()
            except pygame.error:
                pass
            try:
                os.remove(temp_path)
            except OSError:
                pass

    # Public methods
    
    def speak(self, text: str):
        """Generate speech locally and play using synthesize_wav."""
        cleaned = self.clean_text(text)
        if not cleaned:
            return

        # add a filler word because this piper model sometimes does not say the first word
        cleaned = " , " + cleaned
        with self._lock:
            if self.stop_pending:
                self.stop_pending = False
                return
            self._generation += 1
            my_generation = self._generation
            self.stop_requested = False
            self.is_speaking = True
            self.is_paused = False

        try:
            # Create a temporary WAV file
            temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            temp_path = temp_file.name
            temp_file.close()  # We'll reopen it with wave

            # Synthesize directly to WAV (Piper handles the header and all chunks)
            with wave.open(temp_path, 'wb') as wav_file:
                # Optionally pass a SynthesisConfig for speed/tone adjustments
                # from piper import SynthesisConfig
                # config = SynthesisConfig(length_scale=1.1, noise_scale=0.8)
                self.voice.synthesize_wav(cleaned, wav_file, syn_config=None)

            # Check if we were interrupted during synthesis
            with self._lock:
                if my_generation != self._generation or self.stop_requested:
                    os.remove(temp_path)
                    return

            # Load and play the WAV file with Pygame
            pygame.mixer.music.load(temp_path)

            with self._lock:
                if self.stop_requested:
                    return

            pygame.mixer.music.play()

            # Playback loop with pause/resume/stop support
            clock = pygame.time.Clock()
            while True:
                with self._lock:
                    stop_requested = self.stop_requested
                    is_paused = self.is_paused

                # External pause event
                if self.pause_event and self.pause_event.is_set():
                    if not is_paused:
                        pygame.mixer.music.pause()
                        with self._lock:
                            self.is_paused = True
                    self.pause_event.clear()
                    is_paused = True

                # External resume event
                if self.resume_event and self.resume_event.is_set():
                    if is_paused:
                        pygame.mixer.music.unpause()
                        with self._lock:
                            self.is_paused = False
                    self.resume_event.clear()
                    is_paused = False

                if stop_requested:
                    pygame.mixer.music.stop()
                    return

                if is_paused:
                    clock.tick(20)
                    continue

                if not pygame.mixer.music.get_busy():
                    break

                clock.tick(50)

        except Exception as e:
            print(f"[LocalTTS] Error: {e}")
        finally:
            pygame.mixer.music.stop()
            try:
                os.remove(temp_path)
            except OSError:
                pass
            with self._lock:
                if my_generation == self._generation:
                    self.is_speaking = False
                    self.is_paused = False
                    self.stop_pending = False
            print("[LocalTTS] Speech finished.")
    
    def pause(self):
        with self._lock:
            if not self.is_speaking or self.is_paused or self.stop_requested:
                return
            self.is_paused = True
        pygame.mixer.music.pause()

    def resume(self):
        with self._lock:
            if not self.is_speaking or not self.is_paused or self.stop_requested:
                return
            self.is_paused = False
        pygame.mixer.music.unpause()

    def stop(self):
        with self._lock:
            if self.is_speaking:
                self.stop_requested = True
                self.is_paused = False
                self.is_speaking = False
            else:
                self.stop_pending = True
        pygame.mixer.music.stop()

    def isSpeaking(self) -> bool:
        with self._lock:
            return self.is_speaking

    def isPaused(self) -> bool:
        with self._lock:
            return self.is_paused