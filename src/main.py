from wake_word import getWakeWordDetector
from dotenv import load_dotenv

load_dotenv()
detector = getWakeWordDetector()
while(True):
    detector.listenWakeWord()
    print("Wake word detected! Listening for command...")