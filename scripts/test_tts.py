import sys
from pathlib import Path

# Add the src folder to Python's import path.
sys.path.append(
    str(
        Path(__file__).resolve().parents[1]
        / "src"
    )
)

from dotenv import load_dotenv

from stt import getSpeechToText
from tts import getTTSEngine
from wake_word import getWakeWordDetector


EXIT_APPLICATION_COMMANDS = {
    "exit",
    "quit",
    "stop",
    "stop study buddy",
    "shut down",
    "shutdown",
}

NO_MORE_QUESTIONS_RESPONSES = {
    "no",
    "nope",
    "no thanks",
    "no thank you",
    "not now",
    "that is all",
    "that's all",
    "nothing else",
    "i am done",
    "i'm done",
}

YES_RESPONSES = {
    "yes",
    "yeah",
    "yep",
    "sure",
    "yes please",
    "i do",
    "i have another question",
}


def normalizeText(text: str) -> str:
    """
    Normalize transcription for command comparison.
    """

    normalized = text.lower().strip()

    normalized = normalized.translate(
        str.maketrans(
            "",
            "",
            ".,!?;:",
        )
    )

    return " ".join(normalized.split())


def main() -> None:
    load_dotenv()

    print("[Test] Initializing components...")

    wake_word = getWakeWordDetector()
    speech_to_text = getSpeechToText()
    tts = getTTSEngine()

    print("[Test] Ready!")

    should_stop_application = False

    try:
        while not should_stop_application:
            print("\n[Test] Waiting for wake word...")

            wake_word.clearBuffer()
            wake_word.listenWakeWord()

            print("[Test] Wake word detected!")

            greeting = "How can I help you?"

            print(f"[Echo] {greeting}")
            tts.speak(greeting)

            question = (
                speech_to_text
                .listenAndTranscribe()
                .strip()
            )

            if not question:
                print(
                    "[Test] I didn't hear anything. "
                    "Returning to wake-word mode."
                )
                continue

            # Continue accepting questions inside the same session.
            while question:
                print(f"[You] {question}")

                normalized_question = normalizeText(question)

                if normalized_question in EXIT_APPLICATION_COMMANDS:
                    tts.speak("Goodbye!")

                    should_stop_application = True
                    break

                # Fake response because this test does not use RAG.
                response = (
                    f"I heard you say: {question}. "
                    "The speech-to-text and text-to-speech "
                    "pipeline is working correctly."
                )

                print(f"[Echo] {response}")
                tts.speak(response)

                follow_up_prompt = (
                    "Do you have any more questions?"
                )

                print(f"[Echo] {follow_up_prompt}")
                tts.speak(follow_up_prompt)

                print(
                    "[Test] Waiting briefly for a response..."
                )

                follow_up = (
                    speech_to_text
                    .listenAndTranscribe(
                        wait_for_speech_seconds=4.0
                    )
                    .strip()
                )

                # Silence returns to wake-word mode.
                if not follow_up:
                    print(
                        "[Test] No follow-up response detected. "
                        "Returning to wake-word mode."
                    )
                    break

                print(f"[You] {follow_up}")

                normalized_follow_up = normalizeText(
                    follow_up
                )

                # "No" returns to wake-word mode.
                if (
                    normalized_follow_up
                    in NO_MORE_QUESTIONS_RESPONSES
                ):
                    session_end_message = (
                        "Okay. Say Hey Echo whenever you need me."
                    )

                    print(f"[Echo] {session_end_message}")
                    tts.speak(session_end_message)
                    break

                # Exit completely.
                if (
                    normalized_follow_up
                    in EXIT_APPLICATION_COMMANDS
                ):
                    tts.speak("Goodbye!")

                    should_stop_application = True
                    break

                # If the student says only "yes", ask for the question.
                if normalized_follow_up in YES_RESPONSES:
                    question_prompt = "What is your question?"

                    print(f"[Echo] {question_prompt}")
                    tts.speak(question_prompt)

                    next_question = (
                        speech_to_text
                        .listenAndTranscribe()
                        .strip()
                    )

                    if not next_question:
                        print(
                            "[Test] No question was detected. "
                            "Returning to wake-word mode."
                        )
                        break

                    question = next_question
                    continue

                # A direct follow-up becomes the next question.
                question = follow_up

    except KeyboardInterrupt:
        print("\n[Test] Stopped.")


if __name__ == "__main__":
    main()