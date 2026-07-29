from wake_word import getWakeWordDetector
from dotenv import load_dotenv
from tts import getTTSEngine

load_dotenv()

detector = getWakeWordDetector()
tts = getTTSEngine()

while True:
    detector.listenWakeWord()

    message = "Hello! I am Echo. How can I help you?"

    print(message)
    tts.speak(message)