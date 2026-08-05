# src/main.py

import threading

from dotenv import load_dotenv

from rag import BioAssistant
from rag import QuizSession
from stt import getSpeechToText
from tts import getTTSEngine
from wake_word import getWakeWordDetector


# ============================================================
# Commands
# ============================================================

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

QUIZ_START_COMMANDS = {
    "quiz me",
    "ask me a question",
    "start a quiz",
    "quiz",
    "test me",
    "give me a question",
    "i want a quiz",
    "ask me something",
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


# ============================================================
# Text normalization
# ============================================================

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


# ============================================================
# Interruptible TTS
# ============================================================

def speakInterruptibly(
    tts,
    wake_word_detector,
    text: str,
) -> bool:
    """
    Speak text while simultaneously listening
    for the wake word.

    Returns:
        True  -> Hey Echo was detected.
        False -> TTS finished normally.
    """

    print(
        "[Interrupt] Echo is speaking. "
        "Say 'Hey Echo' to interrupt."
    )

    # Make sure the wake-word detector has the microphone.
    wake_word_detector.start()

    stop_event = threading.Event()
    wake_detected = threading.Event()

    # --------------------------------------------------------
    # TTS thread
    # --------------------------------------------------------

    def speak():

        try:
            tts.speak(text)

        except Exception as error:

            print(
                f"[Interrupt] TTS error: {error}"
            )

        finally:

            # Tell wake-word listener that TTS has finished.
            stop_event.set()

    # --------------------------------------------------------
    # Wake-word thread
    # --------------------------------------------------------

    def listen():

        try:

            detected = (
                wake_word_detector.listenWakeWord(
                    stop_event=stop_event
                )
            )

            if detected:

                wake_detected.set()

        except Exception as error:

            print(
                f"[Interrupt] Wake detector error: {error}"
            )

    # --------------------------------------------------------
    # Create threads
    # --------------------------------------------------------

    speech_thread = threading.Thread(
        target=speak,
        daemon=True,
    )

    wake_thread = threading.Thread(
        target=listen,
        daemon=True,
    )

    # Start both simultaneously.
    speech_thread.start()
    wake_thread.start()

    # --------------------------------------------------------
    # Monitor both threads
    # --------------------------------------------------------

    while True:

        # Hey Echo detected.
        if wake_detected.is_set():

            print(
                "[Interrupt] Hey Echo detected!"
            )

            # Immediately stop Echo.
            tts.stop()

            # Tell wake-word listener to stop.
            stop_event.set()

            break

        # TTS finished normally.
        if not speech_thread.is_alive():

            stop_event.set()

            break

        # Small delay.
        threading.Event().wait(0.05)

    # --------------------------------------------------------
    # Wait for TTS thread to finish
    # --------------------------------------------------------

    speech_thread.join(
        timeout=2.0
    )

    # --------------------------------------------------------
    # Release microphone
    # --------------------------------------------------------

    try:

        wake_word_detector.stop()

    except Exception as error:

        print(
            f"[Interrupt] Error releasing microphone: {error}"
        )

    # --------------------------------------------------------
    # Return result
    # --------------------------------------------------------

    return wake_detected.is_set()

# ============================================================
# Quiz Mode loop
# ============================================================

def quiz_loop(assistant, tts, speech_to_text, wake_word_detector):
    print("\n[Quiz] Starting quiz mode.")
    # Create a quiz session with assistant's LLM and retriever
    quiz = QuizSession(assistant.llm, assistant.vectorstore)

    # Initial greeting
    tts.speak("Let's start a quiz. I'll ask you a biology question. Say 'stop' to quit.")

    while True:
        # Get pre‑generated question
        question, topic, _ = quiz.get_next_question()
        print(f"[Quiz] ({topic}) Q: {question}")

        # Speak question (interruptible)
        interrupted = speakInterruptibly(tts, wake_word_detector, question)
        if interrupted:
            tts.speak("Okay, back to study mode.")
            break

        # Listen to answer
        print("[Quiz] Listening for answer...")
        answer = speech_to_text.listenAndTranscribe().strip()
        if answer in EXIT_APPLICATION_COMMANDS:
            tts.speak("Okay, back to study mode.")
            break
        elif not answer:
            tts.speak("I didn't catch that. Let's move on.")
            quiz.record_result(topic, False)   # treat as incorrect
        else:
            print(f"[Student] {answer}")
            # Evaluate with RAG
            print("[Quiz] Checking your answer...")
            feedback = quiz.evaluate(question, answer)
            print(f"[Quiz] Feedback: {feedback}")

            # Determine correctness (simple keyword check to update weakness)
            correct = "correct" in feedback.lower() and "incorrect" not in feedback.lower()
            quiz.record_result(topic, correct)
            
            # Speak feedback (interruptible)
            interrupted = speakInterruptibly(tts, wake_word_detector, feedback)
            if interrupted:
                tts.speak("Alright, back to study mode.")
                break

        # Ask for another question
        tts.speak("Would you like another question?")
        resp = speech_to_text.listenAndTranscribe().strip()
        if not resp or normalizeText(resp) in NO_MORE_QUESTIONS_RESPONSES | EXIT_APPLICATION_COMMANDS:
            tts.speak("Great effort! Returning to study mode.")
            break
        elif normalizeText(resp) in YES_RESPONSES:
            continue
        else:
            tts.speak("I'll take that as a yes.")
            continue

    # Clean up background thread
    quiz.stop()

# ============================================================
# Main
# ============================================================

def main() -> None:

    load_dotenv()

    print(
        "[Main] Initializing Study Buddy..."
    )

    # --------------------------------------------------------
    # Initialize components
    # --------------------------------------------------------

    wake_word_detector = getWakeWordDetector()

    speech_to_text = getSpeechToText()

    assistant = BioAssistant()
    print(f"Vectorstore type: {type(assistant.vectorstore)}") 
    tts = getTTSEngine()

    print(
        "[Main] Study Buddy is ready."
    )

    should_stop_application = False

    try:

        # ====================================================
        # Main application loop
        # ====================================================

        while not should_stop_application:

            print(
                "\n[Main] Waiting for wake word..."
            )

            # Reset previous wake-word detection state.
            wake_word_detector.clearBuffer()

            # ------------------------------------------------
            # Wait for "Hey Echo"
            # ------------------------------------------------

            wake_word_detector.listenWakeWord()

            print(
                "[Main] Wake word detected!"
            )

            # Give microphone to STT.
            wake_word_detector.stop()

            # ------------------------------------------------
            # Greeting
            # ------------------------------------------------

            greeting = (
                "How can I help you?"
            )

            print(
                f"[Echo] {greeting}"
            )

            tts.speak(
                greeting
            )

            # ------------------------------------------------
            # Listen for first question
            # ------------------------------------------------

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

                wake_word_detector.start()

                continue

            # =================================================
            # Conversation loop
            # =================================================

            while question:

                print(
                    f"[Student] {question}"
                )

                normalized_question = normalizeText(
                    question
                )

                # ------------------------------------------------
                # Exit command
                # ------------------------------------------------

                if (
                    normalized_question
                    in EXIT_APPLICATION_COMMANDS
                ):

                    goodbye = "Goodbye."

                    print(
                        f"[Echo] {goodbye}"
                    )

                    tts.speak(
                        goodbye
                    )

                    should_stop_application = True

                    break
                elif normalized_question in QUIZ_START_COMMANDS:
                    quiz_loop(assistant, tts, speech_to_text, wake_word_detector)
                    if not should_stop_application:
                        wake_word_detector.start()
                    break    
                # ------------------------------------------------
                # RAG
                # ------------------------------------------------

                response = assistant.answer(
                    question
                )

                print(
                    f"[Echo] {response}"
                )

                # ------------------------------------------------
                # INTERRUPTIBLE RAG RESPONSE
                # ------------------------------------------------

                interrupted = speakInterruptibly(
                    tts,
                    wake_word_detector,
                    response,
                )

                # ------------------------------------------------
                # Hey Echo interrupted the answer
                # ------------------------------------------------

                if interrupted:

                    print(
                        "[Main] Response interrupted "
                        "by wake word."
                    )

                    # Make sure wake detector is stopped.
                    wake_word_detector.stop()

                    # Give student a new greeting.
                    new_greeting = (
                        "How can I help you?"
                    )

                    print(
                        f"[Echo] {new_greeting}"
                    )

                    tts.speak(
                        new_greeting
                    )

                    # ------------------------------------------------
                    # Listen for the new question
                    # ------------------------------------------------

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

                        break

                    # Go directly to the new question.
                    continue

                # =================================================
                # Normal follow-up flow
                # =================================================

                follow_up_prompt = (
                    "Do you have any more questions?"
                )

                print(
                    f"[Echo] {follow_up_prompt}"
                )

                tts.speak(
                    follow_up_prompt
                )

                print(
                    "[Main] Waiting briefly "
                    "for a response..."
                )

                # ------------------------------------------------
                # Listen for follow-up
                # ------------------------------------------------

                follow_up = (
                    speech_to_text
                    .listenAndTranscribe(
                        wait_for_speech_seconds=4.0
                    )
                    .strip()
                )

                # ------------------------------------------------
                # No response
                # ------------------------------------------------

                if not follow_up:

                    print(
                        "[Main] No follow-up response "
                        "detected. Returning to "
                        "wake-word mode."
                    )

                    break

                print(
                    f"[Student] {follow_up}"
                )

                normalized_follow_up = normalizeText(
                    follow_up
                )

                # ------------------------------------------------
                # No more questions
                # ------------------------------------------------

                if (
                    normalized_follow_up
                    in NO_MORE_QUESTIONS_RESPONSES
                ):

                    session_end_message = (
                        "Okay. Say Hey Echo "
                        "whenever you need me."
                    )

                    print(
                        f"[Echo] {session_end_message}"
                    )

                    tts.speak(
                        session_end_message
                    )

                    break

                # ------------------------------------------------
                # Exit
                # ------------------------------------------------

                if (
                    normalized_follow_up
                    in EXIT_APPLICATION_COMMANDS
                ):

                    goodbye = "Goodbye."

                    print(
                        f"[Echo] {goodbye}"
                    )

                    tts.speak(
                        goodbye
                    )

                    should_stop_application = True

                    break

                # ------------------------------------------------
                # Yes
                # ------------------------------------------------

                if (
                    normalized_follow_up
                    in YES_RESPONSES
                ):

                    question_prompt = (
                        "What is your question?"
                    )

                    print(
                        f"[Echo] {question_prompt}"
                    )

                    tts.speak(
                        question_prompt
                    )

                    next_question = (
                        speech_to_text
                        .listenAndTranscribe()
                        .strip()
                    )

                    if not next_question:

                        print(
                            "[Main] No question was "
                            "detected. Returning to "
                            "wake-word mode."
                        )

                        break

                    question = next_question

                    continue

                # ------------------------------------------------
                # Student directly asked another question
                # ------------------------------------------------

                question = follow_up

            # ====================================================
            # Return microphone to wake-word detector
            # ====================================================

            if not should_stop_application:

                wake_word_detector.start()

    except KeyboardInterrupt:

        print(
            "\n[Main] Study Buddy stopped."
        )

    finally:

        # Always release microphone.
        try:

            wake_word_detector.stop()

        except Exception:

            pass


# ============================================================
# Run application
# ============================================================

if __name__ == "__main__":
    main()