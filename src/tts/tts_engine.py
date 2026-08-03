import asyncio
import edge_tts
import re
import pygame
import tempfile
import os


class TTSEngine:
    def __init__(self):
        self.voice = "en-US-AndrewNeural"

        # Initialize pygame mixer once
        pygame.mixer.init()

    def clean_text(self, text: str) -> str:
        """
        Cleans markdown and formatting characters
        so TTS speaks naturally.
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
            rate="+10%"
          
        )

        await communicate.save(output_file)

    def speak(self, text: str):
        cleaned_text = self.clean_text(text)

        # Create a temporary MP3 file
        with tempfile.NamedTemporaryFile(
            suffix=".mp3",
            delete=False
        ) as temp_file:

            output_file = temp_file.name

        try:
            # Generate speech
            asyncio.run(
                self._speak_async(
                    cleaned_text,
                    output_file
                )
            )

            # Play speech
            pygame.mixer.music.load(output_file)
            pygame.mixer.music.play()

            # Wait until speech finishes
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)

        finally:
            # Release the audio file
            pygame.mixer.music.unload()

            # Delete temporary MP3
            if os.path.exists(output_file):
                os.remove(output_file)