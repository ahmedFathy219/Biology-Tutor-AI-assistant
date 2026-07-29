import asyncio
import edge_tts
import re
import pygame
import tempfile
import os


class TTSEngine:
    def __init__(self):
        self.voice = "en-US-GuyNeural"

        # Initialize pygame mixer once
        pygame.mixer.init()

    def clean_text(self, text: str) -> str:
        """
        Cleans markdown and formatting characters so TTS speaks naturally.
        """

        # Remove markdown symbols
        text = re.sub(r"[*_`#]", "", text)

        # Replace bullet points with pauses
        text = text.replace("- ", ". ")
        text = text.replace("• ", ". ")

        # Remove numbering like "1. ", "2. "
        text = re.sub(r"\d+\.\s*", "", text)

        # Replace new lines with pauses
        text = text.replace("\n", ". ")

        # Remove extra spaces
        text = re.sub(r"\s+", " ", text)

        return text.strip()

    async def _speak_async(self, text: str, output_file: str):
        communicate = edge_tts.Communicate(
            text,
            self.voice,
            rate="+20%"
        )

        await communicate.save(output_file)

    def speak(self, text: str):
        cleaned_text = self.clean_text(text)

        # Create a temporary MP3 file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_file:
            temp_path = temp_file.name

        # Generate speech
        asyncio.run(self._speak_async(cleaned_text, temp_path))

        # Play the audio
        pygame.mixer.music.load(temp_path)
        pygame.mixer.music.play()

        # Wait until playback finishes
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)

        # Release the file
        pygame.mixer.music.unload()

        # Delete the temporary file
        os.remove(temp_path)