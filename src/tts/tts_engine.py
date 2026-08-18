import re
import pygame
import tempfile
import os
import threading

import numpy as np
import requests


class TTSEngine:
    def __init__(self):
        # Normal Pocket TTS server
        self.tts_url = "http://127.0.0.1:8000/tts"

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

    def _play_audio(self, audio_bytes):
        """
        Save the complete WAV response to a temporary file
        and play it.
        """

        temp_file = tempfile.NamedTemporaryFile(
            suffix=".wav",
            delete=False
        )

        temp_path = temp_file.name

        try:
            temp_file.write(audio_bytes)
            temp_file.close()

            pygame.mixer.music.load(temp_path)
            pygame.mixer.music.play()

            clock = pygame.time.Clock()

            while True:

                with self._lock:
                    stop_requested = self.stop_requested
                    is_paused = self.is_paused

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

    def speak(self, text: str):
        """
        Generate the COMPLETE speech response first,
        then play it.

        No streaming.
        No chunks.
        """

        cleaned_text = self.clean_text(text)

        if not cleaned_text:
            return

        with self._lock:
            self.stop_requested = False
            self.is_speaking = True

        try:

            print(
                f"[TTS] Generating speech "
                f"({len(cleaned_text)} characters)..."
            )

            # Request the complete audio from the normal
            # Pocket TTS endpoint.
            response = requests.post(
                self.tts_url,
                data={
                    "text": cleaned_text,
                    "voice_url": (
                        "http://127.0.0.1:8001/"
                        "attenborough-voice.safetensors"
                    ),
                },
                timeout=300,
            )

            response.raise_for_status()

            print(
                "[TTS] Audio generated. "
                "Starting playback..."
            )

            self._play_audio(response.content)

        except requests.RequestException as e:

            print(
                f"[TTS] Request failed: {e}"
            )

        except Exception as e:

            print(
                f"[TTS] TTS error: {e}"
            )

        finally:

            pygame.mixer.music.stop()

            with self._lock:
                self.is_speaking = False
                self.is_paused = False
                self.stop_requested = False

            print("[TTS] Speech finished.")

    def pause(self):
        """
        Pause Echo's current speech.
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
        Resume Echo's speech.
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
        Immediately stop speech.
        """

        with self._lock:
            self.stop_requested = True

        pygame.mixer.music.stop()

    def isSpeaking(self) -> bool:
        """
        Returns True while TTS is speaking.
        """

        with self._lock:
            return self.is_speaking

    def isPaused(self) -> bool:
        """
        Returns True when speech is paused.
        """

        with self._lock:
            return self.is_paused