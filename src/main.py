import threading

from dotenv import load_dotenv

from rag import BioAssistant
from rag import QuizSession
from rag import FlashcardSession
from rag import WeaknessTracker
from stt import getSpeechToText
from tts import getTTSEngine
from wake_word import getWakeWordDetector
from attention import getAttentionMonitor,AttentionState
from utils import load_available_topics
from display import create_display
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

IDK_PHRASES = [
    "i don't know",
    "i dont know",
    "idk",
    "don't know",
    "dont know",
    "not sure",
    "no idea",
    "i have no idea",
    "i'm not sure",
    "i am not sure",
    "i do not know",
    "i don't know the answer",
    "i dont know the answer",
    "no clue",
    "skip",
    "pass",
    "unknown",
]

QUIZ_START_COMMANDS = {
    "quiz me",
    "ask me a question",
    "start a quiz",
    "quiz",
    "test me",
    "give me a question",
    "i want a quiz",
    "ask me something",
    "two"
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
AVAILABLE_TOPICS = load_available_topics()


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
    Returns None if no topic found or the topic is not in AVAILABLE_TOPICS."""
    # Try known patterns
    for command in QUIZ_TOPIC_COMMANDS:
        if normalized_command.startswith(command):
            topic_raw = normalized_command[len(command):].strip()
            # compare to allowed topics
            topic_lower = topic_raw.lower()
            for allowed in AVAILABLE_TOPICS:
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
    normalized = normalized.translate(str.maketrans("", "", ".,!?;:",))

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

    print("[Interrupt] Echo is speaking. " "Say 'Hey Echo' to interrupt.")

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
            print(f"[Interrupt] TTS error: {error}")
        finally:
            # Tell wake-word listener that TTS has finished.
            stop_event.set()

    # --------------------------------------------------------
    # Wake-word thread
    # --------------------------------------------------------

    def listen():
        try:
            detected = wake_word_detector.listenWakeWord(stop_event=stop_event)
            if detected:
                wake_detected.set()

        except Exception as error:
            print(f"[Interrupt] Wake detector error: {error}")

    # --------------------------------------------------------
    # Create threads
    # --------------------------------------------------------
    speech_thread = threading.Thread(target=speak, daemon=True)
    wake_thread = threading.Thread(target=listen,daemon=True)

    # Start both simultaneously.
    speech_thread.start()
    wake_thread.start()

    # --------------------------------------------------------
    # Monitor both threads
    # --------------------------------------------------------
    while True:
        # Hey Echo detected.
        if wake_detected.is_set():
            print("[Interrupt] Hey Echo detected!")

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
 
    # Wait for wake-word thread to exit BEFORE closing stream    
    stop_event.set()
    wake_thread.join(timeout=5.0)

    if wake_thread.is_alive():
        print("[Interrupt] Warning: Wake-word thread did not exit in time.")

    # after wake_thread exits, release microphone
    try:
        wake_word_detector.stop()
    except Exception as error:
        print(f"[Interrupt] Error releasing microphone: {error}")    
    # --------------------------------------------------------
    # Wait for TTS thread to finish
    # --------------------------------------------------------
    speech_thread.join(timeout=2.0)
    return wake_detected.is_set()

# ============================================================
# Quiz Mode loop
# ============================================================

def update_streak(correct: bool) -> int:
    global longest_streak
    global streak

    if correct:
        streak += 1
    else:
        streak = 0

    if streak > longest_streak:
        longest_streak = streak

    print(f"[Quiz] Longest Streak: {longest_streak}")
    print(f"[Quiz] Current Streak: {streak}")

    return streak

def is_idk_response(text: str) -> bool:
        """Return True if the normalized text is clearly an 'I don't know'."""
        # Exact match first
        if text in IDK_PHRASES:
            return True

        # Substring match to catch phrases like "I really don't know"
        for phrase in IDK_PHRASES:
            if phrase in text:
                return True

        return False

def quiz_loop(
    assistant,
    tts,
    speech_to_text,
    wake_word_detector,
    display,
    weakness_tracker=None,
    topic=None,
):
    # Threshold used to decide whether an evaluation is reliable
    # enough to update the weakness tracker and streak.
    CONFIDENCE_THRESHOLD = 0.5

    global should_stop_application
    global streak

    print("\n[Quiz] Starting quiz mode.")

    # ========================================================
    # Topic selection
    # ========================================================
    if topic:
        requested_topic = topic.strip()
        matched_topic = None

        for allowed_topic in AVAILABLE_TOPICS:
            if allowed_topic.lower() == requested_topic.lower():
                matched_topic = allowed_topic
                break

        if matched_topic is not None:
            topic = matched_topic
            greeting = f"Let's quiz on {topic}. Say 'stop' to quit."
        else:
            topic = None
            greeting = (
                "I couldn't find that topic. "
                "Let's review one of your weaker topics instead."
            )

    else:
        # Show the available topic list on the TFT simulator.
        display.showQuizTopics(AVAILABLE_TOPICS)

        topic_prompt = (
            "What topic would you like to study? "
            "Say 'weakest' to review your weak topics."
        )

        print(f"[Echo] {topic_prompt}")
        tts.speak(topic_prompt)

        topic_choice = speech_to_text.listenAndTranscribe()

        if not topic_choice:
            topic = None
            greeting = (
                "I didn't catch a topic. "
                "Let's review one of your weaker topics."
            )
        else:
            normalized_topic = normalizeText(topic_choice)

            if normalized_topic in EXIT_APPLICATION_COMMANDS:
                tts.speak("Alright, Back to study mode.")
                return

            if normalized_topic == "weakest":
                topic = None
                greeting = "Let's review one of your weaker topics."
            else:
                matched_topic = None

                for allowed_topic in AVAILABLE_TOPICS:
                    if allowed_topic.lower() == normalized_topic.lower():
                        matched_topic = allowed_topic
                        break

                if matched_topic is not None:
                    topic = matched_topic
                    greeting = f"Let's quiz on {topic}. Say 'stop' to quit."
                else:
                    topic = None
                    greeting = (
                        "I'm sorry, I couldn't find that topic. "
                        "Let's review one of your weaker topics instead."
                    )

    # ========================================================
    # Create quiz session
    # ========================================================
    quiz = QuizSession(
        assistant.llm,
        assistant.vectorstore,
        weakness_tracker=weakness_tracker,
        focus_topic=topic,
    )

    display_topic = topic if topic is not None else "Weak Topics"

    display.showQuizTime(display_topic)
    tts.speak(greeting)

    question_number = 1
    try:
        # ====================================================
        # Main quiz loop
        # ====================================================
        while True:
            display.showThinking()
            question, topic_used, chunk_text = quiz.get_next_question()

            print(f"[RAG] Retrieved Chunk:\n{chunk_text}\n")
            print(f"[Quiz] ({topic_used}) Q: {question}")

            # Show the question while Echo reads it aloud.
            display.showQuizQuestion(question_number, topic_used, question)

            interrupted = speakInterruptibly(tts, wake_word_detector, question)
            if interrupted:
                tts.speak("Okay, back to study mode.")
                break

            # ------------------------------------------------
            # Listen for answer
            # ------------------------------------------------
            print("[Quiz] Listening for answer...")
            answer = speech_to_text.listenAndTranscribe()

            while not answer:
                feedback = "I didn't catch that. Can you say that again?"
                tts.speak(feedback)
                answer = speech_to_text.listenAndTranscribe()

            normalized_answer = normalizeText(answer)

            if normalized_answer in EXIT_APPLICATION_COMMANDS:
                tts.speak("Okay, back to study mode.")
                break

            # Student can switch topics while already in quiz mode.
            new_topic = extract_topic(normalized_answer)

            if new_topic:
                quiz.set_topic(new_topic)

                display.showQuizTime(new_topic)

                topic_change_message = f"Okay, switching the quiz to {new_topic}."

                tts.speak(topic_change_message)
                question_number = 1
                continue

            print(f"[Student] {answer}")
            print("[Quiz] Checking your answer...")

            # =================================================
            # Evaluate answer
            # =================================================

            if is_idk_response(normalized_answer):
                print("[Quiz] Student doesn't know the answer.")

                # Try to get a short explanation
                try:
                    display.showThinking()
                    explanation = quiz.explain_answer(question, chunk_text)
                    feedback = f"No problem! {explanation}"
                except Exception as e:
                    print(f"[Explanation error] {e}")
                    feedback = "No problem, let's move on."

                result = {
                    "correct": False,
                    "feedback": feedback,
                    "confidence": 1.0,   # we are certain this is incorrect
                }
            else:
                try:
                    display.showThinking()
                    result = quiz.evaluate(question, chunk_text, answer)
                except Exception as e:
                    print(f"[Evaluation error] {e}")
                    result = {
                        "correct": False,
                        "feedback": "Sorry, I had trouble checking that answer. Let's move on.",
                        "confidence": 0.0
                    }
            feedback = result["feedback"]
            confidence = result["confidence"]
            isCorrect = result["correct"]

            print("Correct" if isCorrect else "Wrong")
            print(
                f"[Quiz] Feedback: {feedback} "
                f"(confidence: {confidence:.2f})"
            )

            # Only change performance tracking when the evaluator
            # is confident enough. The visible result still uses
            # the evaluator's returned correct/incorrect value.
            if confidence >= CONFIDENCE_THRESHOLD:
                quiz.record_result(topic_used, isCorrect)
                current_streak = update_streak(isCorrect)
            else:
                current_streak = streak

            # Show result, current streak and the same feedback
            # that Echo is about to speak.
            display.showQuizResult(isCorrect, current_streak, feedback)

            interrupted = speakInterruptibly(tts, wake_word_detector, feedback)
            if interrupted:
                tts.speak("Alright, back to study mode.")
                break

            # =================================================
            # Ask for another question
            # =================================================
            another_message = "Would you like another question?"

            display.showQuizMessage(another_message, current_streak)

            tts.speak(another_message)

            resp = speech_to_text.listenAndTranscribe()
            resp = normalizeText(resp)

            while not resp:
                repeat_message = (
                    "Sorry, I did not catch that. "
                    "Can you please repeat?"
                )

                display.showQuizMessage(repeat_message, current_streak)

                tts.speak(repeat_message)

                resp = speech_to_text.listenAndTranscribe()
                resp = normalizeText(resp)

            new_topic = extract_topic(resp)
            
            if new_topic:
                quiz.set_topic(new_topic)

                display.showQuizTime(new_topic)

                topic_change_message = f"Okay, switching the quiz to {new_topic}."

                tts.speak(topic_change_message)
                question_number = 1
                continue

            if resp in NO_MORE_QUESTIONS_RESPONSES:
                end_message = "Great effort! Returning to study mode."

                display.showQuizMessage(end_message, current_streak)

                tts.speak(end_message)
                break

            elif resp in EXIT_APPLICATION_COMMANDS:
                end_message = "Great effort! Exiting."

                display.showQuizMessage(end_message, current_streak)

                tts.speak(end_message)
                break

            elif resp in YES_RESPONSES:
                next_message = "Great, here is another question."

                display.showQuizMessage(next_message, current_streak)

                tts.speak(next_message)
                question_number += 1
                continue

            else:
                next_message = "I'll take that as a yes."

                display.showQuizMessage(next_message, current_streak)

                tts.speak(next_message)
                question_number += 1
                continue

    finally:
        # Always stop the question-generation thread when quiz mode ends.
        quiz.stop()

# ============================================================
# FlashCard Mode loop
# ============================================================

def flashcard_loop(
    assistant,
    tts,
    speech_to_text,
    wake_word_detector,
    display,
    weakness_tracker=None,
):
    """Interactive flashcard study with self-evaluation and simple spacing."""

    global should_stop_application

    flashcards = FlashcardSession(
        assistant.llm,
        assistant.vectorstore,
        weakness_tracker,
    )

    print("\n[Flashcard] Starting flashcard mode.")

    # ========================================================
    # Topic selection
    # ========================================================
    display.showFlashcardTopics(AVAILABLE_TOPICS)

    topic_prompt = (
        "Flashcard mode. What topic would you like to study? "
        "Say weakest to review your weak topics."
    )

    tts.speak(topic_prompt)

    topic_choice = speech_to_text.listenAndTranscribe()
    topic_choice = normalizeText(topic_choice)

    if topic_choice in EXIT_APPLICATION_COMMANDS:
        exit_message = "Alright, exiting flashcard mode."
        display.showFlashcardMessage(exit_message)
        tts.speak(exit_message)

        return

    if not topic_choice:
        topic_choice = "weakest"

        fallback_message = (
            "I didn't catch that. "
            "We'll review your weakest topics."
        )

        display.showFlashcardMessage(fallback_message)
        tts.speak(fallback_message)

    topic = flashcards.pick_topic(topic_choice)

    start_message = (
        f"Studying {topic}. "
        "I'll show you flashcards one by one."
    )

    display.showFlashcardMode(topic)
    tts.speak(start_message)
    # ========================================================
    # Main flashcard loop
    # ========================================================
    while True:
        # ----------------------------------------------------
        # First present cards that are due for review.
        # ----------------------------------------------------
        due_cards = flashcards.get_due_cards()

        if due_cards:
            tts.speak("There were some due cards, I will show them now.")
            for card in due_cards:
                interrupted = _review_flashcard(
                    card,
                    tts,
                    speech_to_text,
                    wake_word_detector,
                    display,
                    weakness_tracker,
                    flashcards,
                )
                if interrupted:
                    back_message = "Alright, back to study mode."

                    display.showFlashcardMessage(back_message, topic)
                    tts.speak(back_message)
                    return

                next_prompt = "Next flashcard?"

                display.showFlashcardMessage(next_prompt, topic)
                tts.speak(next_prompt)

                cont = speech_to_text.listenAndTranscribe()
                cont = normalizeText(cont)

                while not cont:
                    repeat_message = (
                        "I'm sorry, I did not catch that. "
                        "Can you please repeat your response?"
                    )

                    display.showFlashcardMessage(repeat_message, topic)
                    tts.speak(repeat_message)

                    cont = speech_to_text.listenAndTranscribe()
                    cont = normalizeText(cont)

                if cont in NO_MORE_QUESTIONS_RESPONSES:
                    end_message = (
                        "Great work! Returning to study mode."
                    )

                    display.showFlashcardMessage(end_message, topic)
                    tts.speak(end_message)
                    return

                if cont in EXIT_APPLICATION_COMMANDS:
                    end_message = (
                        "Great work! Exiting application."
                    )

                    display.showFlashcardMessage(end_message, topic)
                    tts.speak(end_message)
                    return

                next_message = "Alright, next card."

                display.showFlashcardMessage(next_message, topic)
                tts.speak(next_message)
            continue

        # ----------------------------------------------------
        # No due cards, generate a new one.
        # ----------------------------------------------------

        print("[FLashCard] here's a new flashcard")
        new_message = "Here's a new flashcard."

        display.showFlashcardMessage(new_message, topic)
        tts.speak(new_message)
        display.showThinking()
        new_card = flashcards.generate_flashcard(topic)

        interrupted = _review_flashcard(
            new_card,
            tts,
            speech_to_text,
            wake_word_detector,
            display,
            weakness_tracker,
            flashcards,
        )
        if interrupted:
            back_message = "Alright, back to study mode."

            display.showFlashcardMessage(back_message, topic)
            tts.speak(back_message)
            return

        # ----------------------------------------------------
        # Ask whether the student wants another card.
        # ----------------------------------------------------
        another_prompt = "Another flashcard?"

        display.showFlashcardMessage(another_prompt, topic)
        tts.speak(another_prompt)

        resp = speech_to_text.listenAndTranscribe()
        resp = normalizeText(resp)

        while not resp:

            repeat_message = (
                "I'm sorry, I did not catch that. "
                "Can you please repeat your response?"
            )

            display.showFlashcardMessage(repeat_message, topic)
            tts.speak(repeat_message)

            resp = speech_to_text.listenAndTranscribe()
            resp = normalizeText(
                resp
            )

        if resp in NO_MORE_QUESTIONS_RESPONSES:

            end_message = (
                "Keep it up! Returning to study mode."
            )

            display.showFlashcardMessage(end_message, topic)
            tts.speak(end_message)
            return

        if resp in EXIT_APPLICATION_COMMANDS:

            end_message = (
                "Great work! Exiting application."
            )

            display.showFlashcardMessage(end_message, topic)
            tts.speak(end_message)
            return

        next_message = "Alright, next card."

        display.showFlashcardMessage(next_message, topic)
        tts.speak(next_message)


# ============================================================
# Flashcard review helper
# ============================================================

def _review_flashcard(
    card,
    tts,
    speech_to_text,
    wake_word_detector,
    display,
    weakness_tracker,
    flashcards,
) -> bool:
    """
    Present one flashcard, wait for reveal, show the answer,
    collect a difficulty rating and schedule the card.
    Returns False to continue flashcardloop
    Returns True to Exit flashcard mode
    """

    topic = card.get(
        "topic",
        "Flashcards",
    )

    # ========================================================
    # Question screen
    # ========================================================
    question_text = f"Question: {card['question']}"


    print(f"\n[Flashcard] {question_text}")

    display.showFlashcardQuestion(topic, card["question"])

    interrupted = speakInterruptibly(tts, wake_word_detector, question_text)
    if interrupted:
        return True

    # ========================================================
    # Wait for reveal command
    # ========================================================
    print("[Flashcard] Waiting for 'reveal'...")

    while True:

        cmd = speech_to_text.listenAndTranscribe(wait_for_speech_seconds=8.0)
        cmd = normalizeText(cmd)

        if cmd in SHOW_ANSWER_COMMANDS:
            break

        if cmd in EXIT_APPLICATION_COMMANDS:
            tts.speak("Okay, back to study mode.")
            return True

        retry_message = (
            "Say reveal when you're ready "
            "to see the answer."
        )
        # Keep the question visible because the screen itself
        # already contains the reveal instruction.
        tts.speak(retry_message)

    # ========================================================
    # Answer screen
    # ========================================================
    answer_text = f"Answer: {card['answer']}"

    print(f"[Flashcard] {answer_text}")

    display.showFlashcardAnswer(topic, card["answer"])

    interrupted = speakInterruptibly(tts, wake_word_detector, answer_text)
    if interrupted:
        return True

    # ========================================================
    # Difficulty screen
    # ========================================================
    difficulty_prompt = (
        "How difficult was that? "
        "Easy, medium, or hard?"
    )

    display.showFlashcardDifficulty(topic)
    tts.speak(difficulty_prompt)

    rating = speech_to_text.listenAndTranscribe(wait_for_speech_seconds=8.0)
    rating = normalizeText(rating)

    if rating not in DIFFICULTY_RATINGS:
        rating = "medium"

        print(
            "[Flashcard] Did not hear a valid rating, "
            "setting to medium by default."
        )

    else:
        print(
            f"[Flashcard] setting to {rating}"
        )

    flashcards.schedule_card(card, rating)

    # ========================================================
    # Confirmation
    # ========================================================
    interval_seconds = card["interval"]

    if interval_seconds < 3600:
        interval_str = f"{interval_seconds // 60} minutes"

    elif interval_seconds < 86400:
        interval_str = f"{interval_seconds // 3600} hours"

    else:
        interval_str = f"{interval_seconds // 86400} days"

    confirm_msg = (
        f"Marked as {rating}. "
        f"It'll appear again in {interval_str}."
    )

    if weakness_tracker is not None:

        if rating == "hard":
            # becomes marked as weak, will be more likey in the future
            weakness_tracker.update(card["topic"], False)

        elif rating == "easy":
            # becomes marked as strong, will be less likely in the future
            weakness_tracker.update(card["topic"], True)

    print(f"[Flashcard] {confirm_msg}")
    display.showFlashcardMessage(confirm_msg, topic)
    tts.speak(confirm_msg)

    return False

# ============================================================
# Main
# ============================================================
def main() -> None:
    global should_stop_application
    global longest_streak
    global streak
    longest_streak = 0
    streak = 0
    should_stop_application = False
    load_dotenv()

    print(
        "[Main] Initializing Study Buddy..."
    )

    display = create_display()

    display.start()
    display.showWakeGuide()

    print(
        "[Display] Echo display started."
    )

    # --------------------------------------------------------
    # Initialize components
    # --------------------------------------------------------
 
    wake_word_detector = getWakeWordDetector()
    speech_to_text = getSpeechToText()

    assistant = BioAssistant()
    attention_monitor = getAttentionMonitor()
    weakness_tracker = WeaknessTracker()

    attentionReady = threading.Event()
    attentionReady.set()

    attention_pause_event = threading.Event()
    attention_resume_event = threading.Event()
    tts = getTTSEngine(
        pause_event=attention_pause_event, resume_event=attention_resume_event
    )

    def handleAttentionState(state):
        if state in {AttentionState.DISTRACTED, AttentionState.NO_FACE}:
            if attentionReady.is_set():
                attentionReady.clear()
                attention_pause_event.set()
                display.showAttentionWarning()   # Still called from attention thread? Could be moved too.
        elif state == AttentionState.FOCUSED:
            if not attentionReady.is_set():
                attentionReady.set()
                attention_resume_event.set()
                display.clearAttentionWarning()

    attention_monitor.setStateCallback(handleAttentionState)

    print(
        "[Main] Study Buddy is ready."
    )

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

            greeting = "How can I help you?"
            print(f"[Echo] {greeting}")
            tts.speak(greeting)

            display.showListening()
            # ------------------------------------------------
            # Listen for first question
            # ------------------------------------------------

            question = speech_to_text.listenAndTranscribe()

            if not question:
                print(
                    "[Main] No question was detected. "
                    "Returning to wake-word mode."
                )

                attention_monitor.stop()
                wake_word_detector.start()
                display.showWakeGuide()

                continue

            # =================================================
            # Conversation loop
            # =================================================

            while question:

                print(f"[Student] {question}")
                normalized_question = normalizeText(question)

                # ------------------------------------------------
                # Exit command
                # ------------------------------------------------
                if normalized_question in EXIT_APPLICATION_COMMANDS:

                    goodbye = "Goodbye."

                    print(f"[Echo] {goodbye}")
                    tts.speak(goodbye)

                    should_stop_application = True
                    break
    
                topic = extract_topic(normalized_question)
                if topic:
                    # quiz mode with specific topic
                    quiz_loop(assistant, tts, speech_to_text, wake_word_detector, display, weakness_tracker=weakness_tracker, topic=topic)
                    if not should_stop_application:
                        wake_word_detector.start()
                    break        
                if normalized_question in QUIZ_START_COMMANDS:
                    # standard quiz mode with weakest random topic
                    quiz_loop(assistant, tts, speech_to_text, wake_word_detector, display, weakness_tracker=weakness_tracker)
                    if not should_stop_application:
                        wake_word_detector.start()
                    break
                if normalized_question in FLASHCARD_START_COMMANDS:
                    flashcard_loop(assistant, tts, speech_to_text, wake_word_detector, display, weakness_tracker)
                    if not should_stop_application:
                        wake_word_detector.start()
                    break   
                # ------------------------------------------------
                # Q&A
                # ------------------------------------------------

                display.showThinking()
                response = assistant.answer(question)

                attentionReady.wait()
                print(f"[Echo] {response}")

                # ------------------------------------------------
                # Split answer into TFT pages
                # --------------------------------------------------------
                # Show only the Answering state on the TFT.
                # The actual answer is not displayed.
                # --------------------------------------------------------

                display.showAnswering("", 1, 1)
                # --------------------------------------------------------
                # Speak the COMPLETE answer normally.
                # No display-page splitting.
                # --------------------------------------------------------

                interrupted = speakInterruptibly(tts, wake_word_detector, response)
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
                    display.showListening()

                    # Give student a new greeting.
                    new_greeting = "How can I help you?"

                    print(f"[Echo] {new_greeting}")
                    tts.speak(new_greeting)

                    # ------------------------------------------------
                    # Listen for the new question
                    # ------------------------------------------------
                    question = speech_to_text.listenAndTranscribe()

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

                follow_up_prompt = ("Do you have any more questions?")
                print(
                    f"[Echo] {follow_up_prompt}"
                )

                tts.speak(follow_up_prompt)
                display.showListening()

                print(
                    "[Main] Waiting briefly "
                    "for a response..."
                )

                # ------------------------------------------------
                # Listen for follow-up
                # ------------------------------------------------

                follow_up = speech_to_text.listenAndTranscribe(wait_for_speech_seconds=4.0)
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

                print(f"[Student] {follow_up}")
                normalized_follow_up = normalizeText(follow_up)

                # ------------------------------------------------
                # No more questions
                # ------------------------------------------------

                if normalized_follow_up in NO_MORE_QUESTIONS_RESPONSES:

                    session_end_message = (
                        "Okay. Say Hey Echo "
                        "whenever you need me."
                    )

                    print(f"[Echo] {session_end_message}")
                    tts.speak(session_end_message)
                    break
                # ------------------------------------------------
                # Exit
                # ------------------------------------------------
                if normalized_follow_up in EXIT_APPLICATION_COMMANDS:

                    goodbye = "Goodbye."

                    print(f"[Echo] {goodbye}")
                    tts.speak(goodbye)

                    should_stop_application = True
                    break
                # ------------------------------------------------
                # Yes
                # ------------------------------------------------
                if normalized_follow_up in YES_RESPONSES:

                    question_prompt = "What is your question?"

                    print(
                        f"[Echo] {question_prompt}"
                    )

                    tts.speak(question_prompt)
                    display.showListening()

                    next_question = speech_to_text.listenAndTranscribe()

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
                attention_monitor.stop()
                wake_word_detector.start()
                display.showWakeGuide()

    except KeyboardInterrupt:

        print(
            "\n[Main] Study Buddy stopped."
        )

    finally:

        try:
            # Permanently close camera + buzzer resources.
            attention_monitor.close()

        except Exception as error:
            print(
                f"[Attention] Shutdown error: {error}"
            )

        try:
            wake_word_detector.stop()

        except Exception as error:
            print(f"[WakeWord] Shutdown error: {error}")
        try:
            display.close()

        except Exception as error:
            print(f"[Display] Shutdown error: {error}")


# ============================================================
# Run application
# ============================================================

if __name__ == "__main__":
    main()