import asyncio
import edge_tts
import os


class TTSEngine:
    def __init__(self):
        self.voice = "en-US-AriaNeural"
        self.output_file = "echo_output.mp3"

    async def _speak_async(self, text: str):
        communicate = edge_tts.Communicate(text, self.voice)
        await communicate.save(self.output_file)

    def speak(self, text: str):
        asyncio.run(self._speak_async(text))

        # Play the generated audio file
        os.startfile(self.output_file)