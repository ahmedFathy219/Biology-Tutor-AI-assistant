import re
import pygame
import tempfile
import os
import threading

import requests


class TTSEngine:
    def __init__(self):
        # Pocket TTS server
        self.tts_url = "http://127.0.0.1:8000/tts"

        # Pre-generated voice profile served locally.
        # The voice profile is created from attenborough-ref.wav
        # and saved as attenborough-voice.safetensors.
        self.voice_url = (
            "http://127.0.0.1:8001/attenborough-voice.safetensors"
        )

        pygame.mixer.init()

        self.is_speaking = False
        self.is_paused = False
        self.stop_requested = False
        self._lock = threading.Lock()

    def clean_text(self, text: str) -> str:
        """
        Cleans markdown and formatting characters
        so TTS speaks naturally.
        """

        text = re.sub(r"[*_`#]", "", text)

        text = text.replace("- ", ". ")
        text = text.replace("• ", ". ")

        text = re.sub(r"\d+\.\s*", "", text)

        text = text.replace("\n", ". ")

        text = re.sub(r"\s+", " ", text)

        return text.strip()

    def _generate_speech(self, text: str, output_file: str):
        """
        Sends text to the running Pocket TTS server using
        the pre-generated Attenborough voice profile.

        The voice profile is served locally through HTTP,
        so Echo does not upload the reference WAV file
        with every TTS request.
        """

        response = requests.post(
            self.tts_url,
            data={
                "text": text,
                "voice_url": self.voice_url,
            },
            timeout=300,
        )

        response.raise_for_status()

        with open(output_file, "wb") as output:
            output.write(response.content)

    def speak(self, text: str):
        """
        Generate and play speech.

        This function can be interrupted using stop().
        """

        cleaned_text = self.clean_text(text)

        if not cleaned_text:
            return

        with self._lock:
            self.stop_requested = False
            self.is_speaking = True

        output_file = None

        try:
            # Create temporary WAV file
            with tempfile.NamedTemporaryFile(
                suffix=".wav",
                delete=False,
            ) as temp_file:

                output_file = temp_file.name

            # Generate speech using Pocket TTS
            self._generate_speech(
                cleaned_text,
                output_file,
            )

            # Check whether stop() was called while
            # Pocket TTS was generating the audio.
            with self._lock:
                if self.stop_requested:
                    return

            # Play speech
            pygame.mixer.music.load(output_file)
            pygame.mixer.music.play()

            clock = pygame.time.Clock()

            while True:

                with self._lock:
                    stop_requested = self.stop_requested
                    is_paused = self.is_paused

                # Completely stop speech
                if stop_requested:
                    pygame.mixer.music.stop()
                    break

                # If attention has paused Echo,
                # remain here without ending speak()
                if is_paused:
                    clock.tick(20)
                    continue

                # Speech genuinely finished
                if not pygame.mixer.music.get_busy():
                    break

                clock.tick(20)

        except requests.RequestException as e:
            print(f"[TTS] Pocket TTS request failed: {e}")

        except Exception as e:
            print(f"[TTS] Error: {e}")

        finally:

            pygame.mixer.music.stop()

            try:
                pygame.mixer.music.unload()
            except pygame.error:
                pass

            if output_file and os.path.exists(output_file):
                try:
                    os.remove(output_file)
                except OSError:
                    pass

            with self._lock:
                self.is_speaking = False
                self.is_paused = False
                self.stop_requested = False

    def pause(self):
        """
        Pause Echo's current speech without losing
        the current position.
        """

        with self._lock:

            if not self.is_speaking:
                return

            if self.is_paused:
                return

            self.is_paused = True

        pygame.mixer.music.pause()

        print("[TTS] Speech paused.")

    def resume(self):
        """
        Continue Echo's speech after an attention pause.
        """

        with self._lock:

            if not self.is_speaking:
                return

            if not self.is_paused:
                return

            self.is_paused = False

        pygame.mixer.music.unpause()

        print("[TTS] Speech resumed.")

    def stop(self):
        """
        Immediately stop currently playing speech.
        """

        with self._lock:
            self.stop_requested = True

        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()

    def isSpeaking(self) -> bool:
        """
        Returns True while TTS is speaking.
        """

        with self._lock:
            return self.is_speaking

    def isPaused(self) -> bool:
        """
        Return True when Echo's speech is paused.
        """

        with self._lock:
            return self.is_paused