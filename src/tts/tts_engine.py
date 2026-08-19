import re
import pygame
import tempfile
import os
import threading

import numpy as np
import requests


class TTSEngine:
    def __init__(self, pause_event=None, resume_event=None):
        # Normal Pocket TTS server
        self.tts_url = "http://127.0.0.1:8000/tts"

        pygame.mixer.init()

        #external events from other threads
        self.pause_event = pause_event
        self.resume_event = resume_event

        self.is_speaking = False
        self.is_paused = False
        self.stop_requested = False
        self.stop_pending = False
        self._generation = 0  
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

    def _play_audio(self, audio_bytes, generation):
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

            #check again if tts was interrupted after writing file
            with self._lock:
                if generation != self._generation or self.stop_requested:
                    print("[DEBUG] 68")
                    return False

            pygame.mixer.music.load(temp_path)

            # Final check before actually starting playback.
            with generation != self._generation or self._lock:
                if self.stop_requested:
                    print("[DEBUG] 76")
                    return False
            pygame.mixer.music.play()
            
            clock = pygame.time.Clock()

            while True:

                with self._lock:
                    stop_requested = self.stop_requested
                    is_paused = self.is_paused

                # External pause request from attention monitor
                if self.pause_event and self.pause_event.is_set():
                    if not is_paused:
                        pygame.mixer.music.pause()
                        with self._lock:
                            self.is_paused = True
                    self.pause_event.clear()
                    is_paused = True

                # External resume request
                if self.resume_event and self.resume_event.is_set():
                    if is_paused:
                        pygame.mixer.music.unpause()
                        with self._lock:
                            self.is_paused = False
                    self.resume_event.clear()
                    is_paused = False

                if stop_requested:
                    pygame.mixer.music.stop()
                    print("[DEBUG] 108")
                    return False

                if is_paused:
                    clock.tick(20)
                    continue

                if not pygame.mixer.music.get_busy():
                    break

                clock.tick(50)
            print("[DEBUG] 119")
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
            print("[DEBUG] 148")
            return

        with self._lock:

            if self.stop_pending:
                self.stop_pending = False
                print("[TTS] Speach cancelled by stop request.")
                return

            self._generation += 1
            my_generation = self._generation
            
            self.stop_requested = False
            self.is_speaking = True
            self.is_paused = False
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

            # before playing ensure
            with self._lock:
                
                if my_generation != self._generation:
                    # abort if another thread called speak()
                    print("[TTS] Supersed by newer speech, discarding.")
                    return
                if self.stop_requested:
                    print("[DEBUG] 191")
                    return
            print(
                "[TTS] Audio generated. "
                "Starting playback..."
            )

            self._play_audio(response.content, my_generation)

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
                #only clear flags if this is still the latest speak() call
                if my_generation == self._generation:
                    self.is_speaking = False
                    self.is_paused = False
                    self.stop_pending = False
            print("[TTS] Speech finished.")

    def pause(self):
        """
        Pause Echo's current speech.
        """

        with self._lock:

            if not self.is_speaking:
                print("[DEBUG] 236")
                return

            if self.is_paused:
                print("[DEBUG] 240")
                return

            if self.stop_requested:
                print("[DEBUG] 244")
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
                print("[DEBUG] 260")
                return

            if not self.is_paused:
                print("[DEBUG] 264")
                return

            if self.stop_requested:
                print("[DEBUG] 268")
                return
            self.is_paused = False

        pygame.mixer.music.unpause()

        print("[TTS] Speech resumed.")

    def stop(self):
        """
        Immediately stop speech.
        """

        with self._lock:
            if self.is_speaking:
                self.stop_requested = True
                self.is_paused = False
                self.is_speaking = False
            else:
                #Speech hasn't started yet -> mark as pending stop
                self.stop_pending = True
        pygame.mixer.music.stop()

    def isSpeaking(self) -> bool:
        """
        Returns True while TTS is speaking.
        """

        with self._lock:
            print("[DEBUG] 297")
            return self.is_speaking

    def isPaused(self) -> bool:
        """
        Returns True when speech is paused.
        """

        with self._lock:
            print("[DEBUG] 306")
            return self.is_paused