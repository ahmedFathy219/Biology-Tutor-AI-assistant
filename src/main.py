# src/main.py

from dotenv import load_dotenv

from rag import BioAssistant
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
    Normalize speech transcription for command comparison.

    Example:
        "No, thank you!" -> "no thank you"
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

    print("[Main] Initializing Study Buddy...")

    wake_word_detector = getWakeWordDetector()
    speech_to_text = getSpeechToText()
    assistant = BioAssistant()
    tts = getTTSEngine()

    print("[Main] Study Buddy is ready.")

    should_stop_application = False

    try:
        while not should_stop_application:
            print("\n[Main] Waiting for wake word...")

            # Reset previous wake-word model audio history.
            wake_word_detector.clearBuffer()

            # Wait until the student says "Hey Echo".
            wake_word_detector.listenWakeWord()

            print("[Main] Wake word detected!")

            greeting = "How can I help you?"

            print(f"[Echo] {greeting}")
            tts.speak(greeting)

            # Listen for the first question.
            question = (
                speech_to_text
                .listenAndTranscribe()
                .strip()
            )

            if not question:
                print(
                    "[Main] No question was detected. "
                    "Returning to wake-word mode."
                )
                continue

            # This inner loop handles one conversation session.
            # Follow-up questions do not require "Hey Echo".
            while question:
                print(f"[Student] {question}")

                normalized_question = normalizeText(question)

                if normalized_question in EXIT_APPLICATION_COMMANDS:
                    goodbye = "Goodbye."

                    print(f"[Echo] {goodbye}")
                    tts.speak(goodbye)

                    should_stop_application = True
                    break

                # Send the student's question to the RAG assistant.
                response = assistant.answer(question)
                # response= "this is a test response"

                print(f"[Echo] {response}")
                tts.speak(response)

                # Ask for another question after finishing the answer.
                follow_up_prompt = (
                    "Do you have any more questions?"
                )

                print(f"[Echo] {follow_up_prompt}")
                tts.speak(follow_up_prompt)

                print(
                    "[Main] Waiting briefly for a response..."
                )

                # Wait four seconds for the student to start speaking.
                follow_up = (
                    speech_to_text
                    .listenAndTranscribe(
                        wait_for_speech_seconds=4.0
                    )
                    .strip()
                )

                # Silence means the conversation session is finished.
                if not follow_up:
                    print(
                        "[Main] No follow-up response detected. "
                        "Returning to wake-word mode."
                    )
                    break

                print(f"[Student] {follow_up}")

                normalized_follow_up = normalizeText(
                    follow_up
                )

                # "No" means return to waiting for "Hey Echo".
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

                # Allow the student to close the entire application.
                if (
                    normalized_follow_up
                    in EXIT_APPLICATION_COMMANDS
                ):
                    goodbye = "Goodbye."

                    print(f"[Echo] {goodbye}")
                    tts.speak(goodbye)

                    should_stop_application = True
                    break

                # If the student only says "yes", ask them to say
                # the actual question.
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
                            "[Main] No question was detected. "
                            "Returning to wake-word mode."
                        )
                        break

                    question = next_question
                    continue

                # If the student directly says another question,
                # treat it as the next question.
                question = follow_up

    except KeyboardInterrupt:
        print("\n[Main] Study Buddy stopped.")


if __name__ == "__main__":
    main()