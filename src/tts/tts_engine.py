import re
import pygame
import tempfile
import os
import threading
import struct
import wave

import numpy as np
import requests


class TTSEngine:
    def __init__(self):
        # Our streaming Pocket TTS server
        self.tts_url = "http://127.0.0.1:8002/tts-stream"

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

    def _read_exact(self, response, size):
        """
        Read exactly `size` bytes from the streaming response.
        """

        data = bytearray()

        while len(data) < size:

            chunk = response.raw.read(
                size - len(data)
            )

            if not chunk:
                return None

            data.extend(chunk)

        return bytes(data)

    def _play_wav_bytes(self, wav_bytes):
        """
        Save one streamed WAV chunk to a temporary file
        and play it with pygame.
        """

        temp_file = tempfile.NamedTemporaryFile(
            suffix=".wav",
            delete=False,
        )

        temp_path = temp_file.name

        try:

            temp_file.write(wav_bytes)
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
        Stream speech from Pocket TTS.

        Playback starts as soon as the first audio chunk
        is generated instead of waiting for the entire
        response.
        """

        cleaned_text = self.clean_text(text)

        if not cleaned_text:
            return

        with self._lock:
            self.stop_requested = False
            self.is_speaking = True

        first_chunk = True

        try:

            print(
                f"[TTS] Starting streaming generation "
                f"({len(cleaned_text)} characters)..."
            )

            response = requests.post(
                self.tts_url,
                data={
                    "text": cleaned_text,
                },
                stream=True,
                timeout=300,
            )

            response.raise_for_status()

            while True:

                # Read 4-byte chunk size
                header = self._read_exact(
                    response,
                    4,
                )

                if header is None:
                    break

                chunk_size = struct.unpack(
                    "!I",
                    header,
                )[0]

                if chunk_size <= 0:
                    break

                # Read actual WAV chunk
                wav_bytes = self._read_exact(
                    response,
                    chunk_size,
                )

                if wav_bytes is None:
                    break

                if first_chunk:

                    print(
                        "[TTS] First audio chunk received. "
                        "Starting playback..."
                    )

                    first_chunk = False

                # Play this chunk before waiting for the next one
                if not self._play_wav_bytes(wav_bytes):
                    break

        except requests.RequestException as e:

            print(
                f"[TTS] Streaming request failed: {e}"
            )

        except Exception as e:

            print(
                f"[TTS] Streaming error: {e}"
            )

        finally:

            pygame.mixer.music.stop()

            with self._lock:
                self.is_speaking = False
                self.is_paused = False
                self.stop_requested = False

            print("[TTS] Streaming finished.")

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