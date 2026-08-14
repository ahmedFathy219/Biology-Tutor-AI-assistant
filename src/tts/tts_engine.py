import asyncio
import edge_tts
import re
import pygame
import tempfile
import os
import threading


class TTSEngine:
    def __init__(self):
        self.voice = "en-US-ChristopherNeural"

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

    async def _speak_async(
        self,
        text: str,
        output_file: str,
    ):
        communicate = edge_tts.Communicate(
            text,
            self.voice,
            rate="+8%",
        )

        await communicate.save(output_file)

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
            # Create temporary MP3 file
            with tempfile.NamedTemporaryFile(
                suffix=".mp3",
                delete=False,
            ) as temp_file:

                output_file = temp_file.name

            # Generate speech
            asyncio.run(
                self._speak_async(
                    cleaned_text,
                    output_file,
                )
            )

            # Check whether stop() was called while
            # Edge TTS was generating the audio.
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