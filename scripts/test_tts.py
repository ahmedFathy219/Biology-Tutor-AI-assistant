import sys
from pathlib import Path

# Add src folder to Python path
sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from dotenv import load_dotenv
from wake_word import getWakeWordDetector
from stt import getSpeechToText
from tts import getTTSEngine


def main():
    load_dotenv()

    print("[Test] Initializing components...")

    wake_word = getWakeWordDetector()
    speech_to_text = getSpeechToText()
    tts = getTTSEngine()

    print("[Test] Ready!")

    try:
        while True:
            print("\n[Test] Waiting for wake word...")

            wake_word.listenWakeWord()

            print("[Test] Wake word detected!")

            question = speech_to_text.listenAndTranscribe()

            if not question:
                print("[Test] I didn't hear anything.")
                continue

            print(f"[You] {question}")

            if question.lower() in {"exit", "quit", "stop"}:
                tts.speak("Goodbye!")
                break

            # Fake assistant response (no RAG)
            response = (
                f"I heard you say: {question}. "
                "The speech-to-text and text-to-speech pipeline is working correctly."
            )

            print(f"[Echo] {response}")

            tts.speak(response)

    except KeyboardInterrupt:
        print("\n[Test] Stopped.")


if __name__ == "__main__":
    main()