# src/main.py

import threading

from dotenv import load_dotenv

from rag import BioAssistant
from rag import QuizSession
from rag import FlashcardSession
from rag import WeaknessTracker
from stt import getSpeechToText
from tts import getTTSEngine
from wake_word import getWakeWordDetector
from attention import getAttentionMonitor
from utils import load_config
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

QUIZ_TOPIC_COMMANDS = {
    "quiz me on ",
    "quiz on ",
    "quiz me about ",
    "quiz about ",
    "ask me a question on ",
    "ask me a question about ",
    "ask me something about ",
    "ask me something on ", 
}

#load allowed topics from utils/config.json
ALLOWED_TOPICS = load_config()["ALLOWED_TOPICS"]


YES_RESPONSES = {
    "yes",
    "yeah",
    "yep",
    "sure",
    "yes please",
    "i do",
    "i have another question",
}


FLASHCARD_START_COMMANDS = {
    "flashcards",
    "start flashcards",
    "flashcard mode",
    "study flashcards",
    "flashcard",
    "flash card",
    "flash",
    "cards",
    "three"
}

# Inside the flashcard loop we’ll use these
SHOW_ANSWER_COMMANDS = {
    "show answer", "answer", "reveal", "show", "flip"
}
DIFFICULTY_RATINGS = {
    "easy", "medium", "hard"
}

# helper function for quiz mode with specific topic
def extract_topic(normalized_command: str) -> str | None:
    """Check if the command contains a known topic phrase and return the topic.
    Returns None if no topic found or the topic is not in ALLOWED_TOPICS."""
    # Try known patterns
    for command in QUIZ_TOPIC_COMMANDS:
        if normalized_command.startswith(command):
            topic_raw = normalized_command[len(command):].strip()
            # compare to allowed topics
            topic_lower = topic_raw.lower()
            for allowed in ALLOWED_TOPICS:
                if allowed.lower() == topic_lower:
                    return allowed
            # if not found return the topic read i title case
            return topic_raw.title()
    # No pattern matched
    return None



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

def quiz_loop(assistant, tts, speech_to_text, wake_word_detector, weakness_tracker=None, topic=None):
    #threshold used to determine how correct the user is
    CONFIDENCE_THRESHOLD = 0.7
    
    print("\n[Quiz] Starting quiz mode.")
    # Create a quiz session with assistant's LLM and retriever

    if topic:
        if topic.strip().title() in ALLOWED_TOPICS:
            greeting = f"Let's quiz on {topic}. Say 'stop' to quit."
            quiz = QuizSession(assistant.llm, assistant.vectorstore, weakness_tracker=weakness_tracker, focus_topic=topic.strip().title())
        else:
            tts.speak(f"Sorry, I don't have material on {topic}. Let's do a random topic instead.")
            topic = None
    else:
        greeting = "Let's start a quiz. I'll ask you a biology question. Say 'stop' to quit."
        quiz = QuizSession(assistant.llm, assistant.vectorstore, weakness_tracker=weakness_tracker)
    # Initial greeting
    tts.speak(greeting)

    while True:
        # Get pre‑generated question
        question, topic_used, _ = quiz.get_next_question()
        print(f"[Quiz] ({topic_used}) Q: {question}")

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
            quiz.record_result(topic_used, False)   # treat as incorrect
       
        
        new_topic = extract_topic(normalizeText(answer))
        if new_topic:
            # start a new quiz session with a different topic
            quiz.stop()
            quiz_loop(assistant, tts, speech_to_text, wake_word_detector, topic=new_topic)
            return
        else:
            print(f"[Student] {answer}")
            print("[Quiz] Checking your answer...")

            result = quiz.evaluate(question, answer)
            feedback = result["feedback"]
            confidence = result["confidence"]
            isCorrect = result["correct"]
            print("Correct" if isCorrect else "")
            print(f"[Quiz] Feedback: {feedback} (confidence: {confidence:.2f})")

            #only record result if confidence is highe enough
            if confidence >= CONFIDENCE_THRESHOLD:
                quiz.record_result(topic_used, isCorrect)
                
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
# FlashCard Mode loop
# ============================================================

def flashcard_loop(assistant, tts, speech_to_text, wake_word_detector, weakness_tracker=None):
    """Interactive flashcard study with self‑evaluation and simple spacing."""
    flashcards = FlashcardSession(assistant.llm, assistant.vectorstore, weakness_tracker)
    print("\n[Flashcard] Starting flashcard mode.")

    tts.speak("Flashcard mode. What topic would you like to study? Say 'weakest' for your weak topics.")
    topic_choice = speech_to_text.listenAndTranscribe().strip()
    topic_choice = normalizeText(topic_choice)
    if not topic_choice or topic_choice in EXIT_APPLICATION_COMMANDS:
        tts.speak("Okay, back to study mode.")
        return

    topic = flashcards.pick_topic(topic_choice)
    tts.speak(f"Studying {topic}. I'll show you flashcards one by one.")

    while True:
        # 1. First, present any due cards
        due_cards = flashcards.get_due_cards()
        if due_cards:
            for card in due_cards:
                interrupted = _review_flashcard(card, tts, speech_to_text, wake_word_detector, flashcards)
                if interrupted:
                    tts.speak("Alright, back to study mode.")
                    return
                # After each card ask if they want to continue
                tts.speak("Next flashcard?")
                cont = speech_to_text.listenAndTranscribe().strip()
                if not cont or normalizeText(cont) in NO_MORE_QUESTIONS_RESPONSES | EXIT_APPLICATION_COMMANDS:
                    tts.speak("Great work! Returning to study mode.")
                    return
            continue   # loop again to check for more due cards

        # 2. No due cards then generate a new one
        tts.speak("Here's a new flashcard.")
        new_card = flashcards.generate_flashcard(topic)
        interrupted = _review_flashcard(new_card, tts, speech_to_text, wake_word_detector, flashcards)
        if interrupted:
            tts.speak("Alright, back to study mode.")
            return

        # Ask for continuation
        tts.speak("Another flashcard?")
        resp = speech_to_text.listenAndTranscribe().strip()
        if not resp or normalizeText(resp) in NO_MORE_QUESTIONS_RESPONSES | EXIT_APPLICATION_COMMANDS:
            tts.speak("Keep it up! Returning to study mode.")
            return
        # else continue loop

# helper for flashcard_loop
def _review_flashcard(card, tts, speech_to_text, wake_word_detector, flashcards) -> bool:
    """
    Present a single flashcard: show question, wait for user to say: 'show answer',
    reveal answer, ask for difficulty rating, and schedule.
    """
    # Speak question (interruptible)
    question_text = f"Question: {card['question']}"
    print(f"\n[Flashcard] {question_text}")
    #
    # display question on lcd screen here
    #
    interrupted = speakInterruptibly(tts, wake_word_detector, question_text)
    if interrupted:
        return True

    # Wait for "show answer"
    print("[Flashcard] Waiting for 'show answer'...")
    while True:
        cmd = speech_to_text.listenAndTranscribe(wait_for_speech_seconds=5.0).strip()
        if normalizeText(cmd) in SHOW_ANSWER_COMMANDS:
            break
        if not cmd or normalizeText(cmd) in EXIT_APPLICATION_COMMANDS:
            tts.speak("Okay, moving on.")
            return False   # treat as skip
        tts.speak("Say 'show answer' when you're ready.")

    # Reveal answer (interruptible)
    answer_text = f"Answer: {card['answer']}"
    print(f"[Flashcard] {answer_text}")
    #
    # display answer on lcd screen here
    #
    interrupted = speakInterruptibly(tts, wake_word_detector, answer_text)
    if interrupted:
        return True

    # Ask difficulty rating
    tts.speak("How difficult was that? Easy, medium, or hard?")
    rating = speech_to_text.listenAndTranscribe(wait_for_speech_seconds=4.0).strip()
    rating = normalizeText(rating)
    if rating not in DIFFICULTY_RATINGS:
        rating = "medium"   # default
        print("[Flashcard] did not hear you, setting to mediam as default")
    else:
        print(f"[Flashcard] setting to {rating}")
    flashcards.schedule_card(card, rating)

    # Verbal confirmation of rating choice with human‑readable interval
    interval_seconds = card["interval"]
    if interval_seconds < 3600:
        interval_str = f"{interval_seconds // 60} minutes"
    elif interval_seconds < 86400:
        interval_str = f"{interval_seconds // 3600} hours"
    else:
        interval_str = f"{interval_seconds // 86400} days"

    confirm_msg = f"Marked as {rating}. It'll appear again in {interval_str}."
    print(f"[Flashcard] {confirm_msg}")
    tts.speak(confirm_msg)

    return False

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
    attention_monitor = getAttentionMonitor()

    weakness_tracker = WeaknessTracker()
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
            attention_monitor.start()

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
                
                topic = extract_topic(normalized_question)
                if topic:
                    # quiz mode with specific topic
                    quiz_loop(assistant, tts, speech_to_text, wake_word_detector, weakness_tracker=weakness_tracker, topic=topic)
                    if not should_stop_application:
                        wake_word_detector.start()
                    break        
                if normalized_question in QUIZ_START_COMMANDS:
                    # standard quiz mode with weakest random topic
                    quiz_loop(assistant, tts, speech_to_text, wake_word_detector, weakness_tracker=weakness_tracker)
                    if not should_stop_application:
                        wake_word_detector.start()
                    break
                if normalized_question in FLASHCARD_START_COMMANDS:
                    flashcard_loop(assistant, tts, speech_to_text, wake_word_detector, weakness_tracker)
                    if not should_stop_application:
                        wake_word_detector.start()
                    break   
                # ------------------------------------------------
                # Q&A
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