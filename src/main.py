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
from attention import getAttentionMonitor,AttentionState
from utils import load_available_topics
from display import TftDisplay
from display.textPagination import paginateText
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

def update_streak(correct: bool):
    global longest_streak
    global streak

    if correct:
        streak+=1   
    else:
        streak = 0    
    if streak > longest_streak:
        longest_streak = streak

    print(f"[Quiz] Longest Streak: {longest_streak}")
    print(f"[Quiz] Current Streak: {streak}")
    # display streak on screan laterr

def quiz_loop(assistant, tts, speech_to_text, wake_word_detector, weakness_tracker=None, topic=None):
    #threshold used to determine how correct the user is
    CONFIDENCE_THRESHOLD = 0.5
    global should_stop_application
    print("\n[Quiz] Starting quiz mode.")
    # Create a quiz session with assistant's LLM and retriever

    if topic:
        topic = topic.strip().title()
        if topic in AVAILABLE_TOPICS:
            greeting = f"Let's quiz on {topic}. Say 'stop' to quit."
        else:
            greeting = f"Sorry, I don't have material on {topic}. Let's do a weak topic instead. Say 'stop' to quit"
            topic = None
    else: 
        tts.speak("What topic would you like to study? Say 'weakest' to review your weak topics.")
        topic = topic.strip().title()
        if topic in AVAILABLE_TOPICS:
            greeting = f"Let's quiz on {topic}. Say 'stop' to quit."
        else:
            greeting = f"Sorry, I don't have material on {topic}. Let's do a weak topic instead. Say 'stop' to quit"
            topic = None

    quiz = QuizSession(assistant.llm, assistant.vectorstore, weakness_tracker=weakness_tracker, focus_topic=topic)

    # Initial greeting
    tts.speak(greeting)
    while True:
        # Get pre‑generated question
        question, topic_used, chunk_text = quiz.get_next_question()
        print(f"[RAG] Retreived Chunk:\n{chunk_text}\n")
        print(f"[Quiz] ({topic_used}) Q: {question}")
        
        # Speak question (interruptible)
        interrupted = speakInterruptibly(tts, wake_word_detector, question)
        if interrupted:
            tts.speak("Okay, back to study mode.")
            should_stop_application = True
            break
            
        # Listen to answer
        print("[Quiz] Listening for answer...")
        answer = speech_to_text.listenAndTranscribe().strip()

        if answer in EXIT_APPLICATION_COMMANDS:
            tts.speak("Okay, back to study mode.")
            should_stop_application = True
            break
        elif not answer:
            tts.speak("I didn't catch that. Let's move on.")
            quiz.record_result(topic_used, False)   # treat as incorrect
            update_streak(False)
            continue
        
        #student said eg. "quiz me on {new topic}"    
        new_topic = extract_topic(normalizeText(answer))
        if new_topic:
            # change quiz topic
            quiz.set_topic(new_topic)
            continue

        print(f"[Student] {answer}")
        print("[Quiz] Checking your answer...")

        result = quiz.evaluate(question, chunk_text, answer)
        feedback = result["feedback"]
        confidence = result["confidence"]
        isCorrect = result["correct"]
        print("Correct" if isCorrect else "Wrong")
        print(f"[Quiz] Feedback: {feedback} (confidence: {confidence:.2f})")

        #only record result if confidence is highe enough
        if confidence >= CONFIDENCE_THRESHOLD:
            quiz.record_result(topic_used, isCorrect)
            update_streak(True)
        
        # Speak feedback (interruptible)
        interrupted = speakInterruptibly(tts, wake_word_detector, feedback)
        if interrupted:
            tts.speak("Alright, back to study mode.")
            break

        # Ask for another question
        tts.speak("Would you like another question?")
        resp = speech_to_text.listenAndTranscribe().strip()
        resp = normalizeText(resp)

        while not resp:
            tts.speak("Sorry, I did not catch that, can you please repeat?")
            resp = normalizeText(speech_to_text.listenAndTranscribe().strip())
        if resp in NO_MORE_QUESTIONS_RESPONSES:
            tts.speak("Great effort! Returning to study mode.")
            break
        elif resp in EXIT_APPLICATION_COMMANDS:
            tts.speak("Great effort! exiting.")
            should_stop_application = True
            break
        elif resp in YES_RESPONSES:
            tts.speak("Great, here is another question.")
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
    global should_stop_application
    flashcards = FlashcardSession(assistant.llm, assistant.vectorstore, weakness_tracker)
    print("\n[Flashcard] Starting flashcard mode.")

    tts.speak("Flashcard mode. What topic would you like to study? Say 'weakest' to review your weak topics.")
    topic_choice = speech_to_text.listenAndTranscribe().strip()
    topic_choice = normalizeText(topic_choice)
    if topic_choice in EXIT_APPLICATION_COMMANDS:
        should_stop_application = True
        tts.speak("Altright, exiting application.")
        return
    if not topic_choice:
        tts.speak("I did'nt catch that, we will review weakest topics.")
    topic = flashcards.pick_topic(topic_choice)
    tts.speak(f"Studying {topic}. I'll show you flashcards one by one.")

    while True:
        # 1. First, present any due cards
        due_cards = flashcards.get_due_cards()
        if due_cards:
            for card in due_cards:
                interrupted = _review_flashcard(card, tts, speech_to_text, weakness_tracker, wake_word_detector, flashcards)
                if interrupted:
                    tts.speak("Alright, back to study mode.")
                    return
                # After each card ask if they want to continue
                tts.speak("Next flashcard?")
                cont = speech_to_text.listenAndTranscribe().strip()
                cont = normalizeText(cont)
                while not cont:
                    tts.speak("I'm sorry, i did not catch that, can you please repeat your response?")
                    cont = speech_to_text.listenAndTranscribe().strip()
                    cont = normalizeText(cont)
                if cont in NO_MORE_QUESTIONS_RESPONSES:
                    tts.speak("Great work! Returning to study mode.")
                    return
                if cont in EXIT_APPLICATION_COMMANDS:
                    tts.speak("Great work! Exiting application.")
                    should_stop_application = True
                    return
                tts.speak("Alright, Next Card.")
            continue   # loop again to check for more due cards

        print("[DEBUG] here the new flashcard")        
        # 2. No due cards then generate a new one
        tts.speak("Here's a new flashcard.")
        new_card = flashcards.generate_flashcard(topic)
        interrupted = _review_flashcard(new_card, tts, speech_to_text, wake_word_detector, weakness_tracker, flashcards)
        if interrupted:
            tts.speak("Alright, back to study mode.")
            return

        # Ask for continuation
        tts.speak("Another flashcard?")
        resp = speech_to_text.listenAndTranscribe().strip()
        resp = normalizeText(resp)
        while not resp:
            tts.speak("I'm sorry, i did not catch that, can you please repeat your response?")
            resp = speech_to_text.listenAndTranscribe().strip()
            resp = normalizeText(resp)
        if resp in NO_MORE_QUESTIONS_RESPONSES:
            tts.speak("Keep it up! Returning to study mode.")
            return
        if resp in EXIT_APPLICATION_COMMANDS:
            tts.speak("Great work! Exiting application.")
            should_stop_application = True
            return
        tts.speak("Alright, Next Card.")
        # else continue loop

# helper for flashcard_loop
def _review_flashcard(card, tts, speech_to_text, wake_word_detector, weakness_tracker, flashcards) -> bool:
    """
    Present a single flashcard: show question, wait for user to say: 'show answer',
    reveal answer, ask for difficulty rating, and schedule.
    """
    global should_stop_application
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
        cmd = normalizeText(cmd)
        if cmd in SHOW_ANSWER_COMMANDS:
            break
        if not cmd:
            tts.speak("Okay, moving on.")
            return False   # treat as skip
        if cmd in EXIT_APPLICATION_COMMANDS:
             should_stop_application = True
             return True # interrupt    
        tts.speak("Say 'show answer' when you're ready.")

    answer_text = f"Answer: {card['answer']}"
    print(f"[Flashcard] {answer_text}")
    #
    # display answer on lcd screen here (not yet implemented)
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

    if rating == "hard": #mark as weak topic
        weakness_tracker.update(card['topic'], False)
    elif rating == "easy": #mark as strong topic
        weakness_tracker.update(card['topic'], True)

    print(f"[Flashcard] {confirm_msg}")
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

    display = TftDisplay()

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
    print(f"Vectorstore type: {type(assistant.vectorstore)}") 
    tts = getTTSEngine()

    attentionReady = threading.Event()
    
    attentionReady.set()

    def handleAttentionState(
        state: AttentionState,
    ) -> None:
    
        # ====================================================
        # Student became distracted
        # ====================================================
    
        if state in {
            AttentionState.DISTRACTED,
            AttentionState.NO_FACE,
        }:
    
            # Only trigger once.
            if attentionReady.is_set():
    
                print(
                    "[Main] Student distracted. "
                    "Pausing interaction."
                )
    
                # Stop the rest of Echo from advancing.
                attentionReady.clear()
    
                # Override current TFT screen.
                display.showAttentionWarning()
    
                # Pause speech if Echo is currently speaking.
                tts.pause()
    
            return
    
    
        # ====================================================
        # Student is focused again
        # ====================================================
    
        if state == AttentionState.FOCUSED:
    
            if not attentionReady.is_set():
    
                print(
                    "[Main] Attention restored. "
                    "Resuming interaction."
                )
    
                # Restore whatever screen Echo should
                # currently be displaying.
                display.clearAttentionWarning()
    
                # Continue speech from the same position.
                tts.resume()
    
                # Allow the rest of Echo to continue.
                attentionReady.set()

    attention_monitor.setStateCallback(
        handleAttentionState
    )

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

            greeting = (
                "How can I help you?"
            )

            print(
                f"[Echo] {greeting}"
            )

            tts.speak(
                greeting
            )

            display.showListening()

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

                attention_monitor.stop()

                wake_word_detector.start()
                display.showWakeGuide()

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

                display.showThinking()

                response = assistant.answer(
                    question
                )

                attentionReady.wait()

                print(
                    f"[Echo] {response}"
                )

                # ------------------------------------------------
                # Split answer into TFT pages
                # ------------------------------------------------

                answerPages = paginateText(
                    response
                )

                totalPages = len(answerPages)

                interrupted = False


               # ------------------------------------------------
                # Display and speak each page together
                # ------------------------------------------------

                interrupted = False

                for pageIndex, pageText in enumerate(
                    answerPages
                ):
                    attentionReady.wait()

                    pageNumber = pageIndex + 1

                    # Show the page Echo is about to speak
                    display.showAnswering(
                        pageText,
                        pageNumber,
                        totalPages,
                    )
                    speechPageText = pageText.replace( "\n", " ")


                    # Speak exactly this page.
                    # TTSEngine.speak() blocks until this page
                    # has completely finished playing.
                    interrupted = speakInterruptibly(
                        tts,
                        wake_word_detector,
                        pageText,
                    )
                    if interrupted:
                        break

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
                display.showListening()

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

                    display.showListening()

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

        except Exception:
            pass

        try:
            display.close()

        except Exception:
            pass


# ============================================================
# Run application
# ============================================================

if __name__ == "__main__":
    main()