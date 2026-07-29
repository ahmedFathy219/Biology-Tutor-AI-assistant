from wake_word import getWakeWordDetector
from rag import BioAssistant
from dotenv import load_dotenv
from tts import getTTSEngine
import time

load_dotenv()

assistant = BioAssistant()

detector = getWakeWordDetector()
tts = getTTSEngine()

while True:
    detector.listenWakeWord()

    print("Wake word detected! Listening for command...")

    # Placeholder for STT
    transcription = input("Type your question (or 'exit' to stop): ")

    if transcription.lower() == "exit":
        break

    # Query the assistant
    response = assistant.answer(transcription)

    # Output to console
    print(f"Echo: {response}")

    # Speak the response
    tts.speak(response)

    # Wait before listening again
    time.sleep(5)