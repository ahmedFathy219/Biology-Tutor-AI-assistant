from dotenv import load_dotenv

from stt import getSpeechToText
from wake_word import getWakeWordDetector


def main() -> None:
    load_dotenv()

    print("[Main] Initializing Study Buddy...")

    wake_word_detector = getWakeWordDetector()

    # Load the Whisper model only once.
    speech_to_text = getSpeechToText()

    print("[Main] Study Buddy is ready.")

    try:
        while True:
            print("\n[Main] Waiting for wake word...")

            # This waits only for “Hey Echo”.
            wake_word_detector.listenWakeWord()

            print(
                "[Main] Wake word detected! "
                "Now listening for your question..."
            )

            # This records and transcribes the following sentence.
            question = speech_to_text.listenAndTranscribe()

            if not question:
                print(
                    "[Main] No question was detected. "
                    "Please try again."
                )
                continue

            print(f"\n[Student] {question}")

            # Later:
            # answer = rag.answerQuestion(question)
            # text_to_speech.speak(answer)

    except KeyboardInterrupt:
        print("\n[Main] Study Buddy stopped.")


if __name__ == "__main__":
    main()