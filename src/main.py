# src/main.py

from dotenv import load_dotenv
import time
from rag import BioAssistant
from stt import getSpeechToText
from tts import getTTSEngine
from wake_word import getWakeWordDetector


def main() -> None:
    load_dotenv()

    print("[Main] Initializing Study Buddy...")

    # Initialize each major component only once.
    wake_word_detector = getWakeWordDetector()
    speech_to_text = getSpeechToText()
    assistant = BioAssistant()
    tts = getTTSEngine()

    print("[Main] Study Buddy is ready.")

    try:
        while True:
            print("\n[Main] Waiting for wake word...")

            # 1. Wait for "Hey Echo"
            wake_word_detector.listenWakeWord()

            print(
                "[Main] Wake word detected! "
                "Now listening for your question..."
            )

            # 2. Record and transcribe the spoken question
            question = speech_to_text.listenAndTranscribe()

            if not question:
                print(
                    "[Main] No question was detected. "
                    "Please try again."
                )
                continue

            print(f"[Student] {question}")

            # Optional spoken or typed exit command
            if question.strip().lower() in {
                "exit",
                "quit",
                "stop study buddy",
            }:
                print("[Main] Ending the Study Buddy session.")
                break

            # 3. Send the transcription to the biology assistant
            response = assistant.answer(question)

            # 4. Show the response in the console
            print(f"[Echo] {response}")

            # 5. Speak the response aloud
            tts.speak(response)
            time.sleep(2.0)

    except KeyboardInterrupt:
        print("\n[Main] Study Buddy stopped.")


if __name__ == "__main__":
    main()