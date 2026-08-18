from src.tts.tts_engine import TTSEngine

tts = TTSEngine()

print("Testing Pocket TTS...")

tts.speak(
    "Hello! This is Echo speaking with the new voice.Here, in the dim, dappled light of the ancient forest floor, an extraordinary spectacle is about to unfold. If we remain completely silent, we might catch a glimpse of one of nature’s most magnificent and elusive creatures, perfectly adapted to a world that is rapidly changing around it. Notice the remarkable intricate patterns along its back—a breathtaking triumph of millions of years of evolutionary design. It is a poignant, fragile reminder of the immense beauty and sheer complexity of life on our planet, and why we must do everything in our power to protect it."
)

print("TTS test finished.")