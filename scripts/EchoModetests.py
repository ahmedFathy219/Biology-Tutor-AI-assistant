import sys
from pathlib import Path
sys.path.append(
    str(
        Path(__file__).resolve().parents[1]
        / "src"
    )
)

from rag import QuizSession
from rag import BioAssistant
from rag import WeaknessTracker
from rag import FlashcardSession
from utils import load_config
ALLOWED_TOPICS = load_config()["ALLOWED_TOPICS"]

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

sys.path.append(
    str(
        Path(__file__).resolve().parents[1]
        / "src"
    )
)

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

def quiz_loop(assistant, weakness_tracker=None, topic=None):
    #threshold used to determine how correct the user is
    CONFIDENCE_THRESHOLD = 0.7
    print("\n[Quiz] Starting quiz mode.")
    # Create a quiz session with assistant's LLM and retriever

    if topic:
        topic = topic.strip().title()
        if topic in ALLOWED_TOPICS:
            greeting = f"Let's quiz on {topic}. Say 'stop' to quit."
        else:
            greeting = f"Sorry, I don't have material on {topic}. Let's do a random topic instead. Say 'stop' to quit"
            topic = None
    else: 
        greeting = "Let's start a quiz on a random topic. I'll ask you a biology question. Say 'stop' to quit."
    quiz = QuizSession(assistant.llm, assistant.vectorstore, weakness_tracker=weakness_tracker, focus_topic=topic)

    # Initial greeting
    print(f"[TTS] {greeting}")
    while True:
        # Get pre‑generated question
        question, topic_used, chunk = quiz.get_next_question()
        print(f"[Quiz] ({topic_used}) Q: {question}")

        # Speak question (interruptible)
        print(f"Topic: {topic}")
        print()
        print(f"Reference: {chunk}")
        print()
        print(f"Question: {question}")

            
        # Listen to answer
        print("[Quiz] Listening for answer...")
        answer = input("[STT] Enter answer>>>")

        if answer in EXIT_APPLICATION_COMMANDS:
            print("[TTS] Okay, back to study mode.")
            should_stop_application = True
            break
        elif not answer:
            print("[TTS] I didn't catch that. Let's move on.")
            quiz.record_result(topic_used, False)   # treat as incorrect
            continue
        
        #student said eg. "quiz me on {new topic}"    
        new_topic = extract_topic(normalizeText(answer))
        if new_topic:
            # change quiz topic
            print(f"[TTS] changed quiz topic to {new_topic}")
            quiz.set_topic(new_topic)
            continue

        print(f"[Student] {answer}")
        print("[Quiz] Checking your answer...")

        result = quiz.evaluate(question, chunk, answer)
        feedback = result["feedback"]
        confidence = result["confidence"]
        isCorrect = result["correct"]
        print("Correct" if isCorrect else "")
        print(f"[Quiz] Feedback: {feedback} (confidence: {confidence:.2f})")

        #only record result if confidence is highe enough
        if confidence >= CONFIDENCE_THRESHOLD:
            quiz.record_result(topic_used, isCorrect)
            
        # Speak feedback (interruptible)
        

        # Ask for another question
        print("[TTS] would you like another question?")
        resp = input("[STT] Enter response>>>")
        resp = normalizeText(resp)
        if not resp or resp in NO_MORE_QUESTIONS_RESPONSES:
            print("[TTS] Great effort! Returning to study mode.")
            break
        elif resp in EXIT_APPLICATION_COMMANDS:
            print("[TTS] Great effort! exiting.")
            should_stop_application = True
            break
        elif resp in YES_RESPONSES:
            continue
        else:
            print("[TTS] I'll take that as a yes.")
            continue

    # Clean up background thread
    quiz.stop()


def flashcard_loop(assistant, weakness_tracker=None):
    """Interactive flashcard study with self‑evaluation and simple spacing."""
    flashcards = FlashcardSession(assistant.llm, assistant.vectorstore, weakness_tracker)
    print("\n[Flashcard] Starting flashcard mode.")

    print("[TTS] Flashcard mode. What topic would you like to study? Say 'weakest' to review your weak topics.")
    topic_choice = input("[STT] speak: ")
    topic_choice = normalizeText(topic_choice)
    if topic_choice in EXIT_APPLICATION_COMMANDS:
        should_stop_application = True
        print("[TTS] Altright, exiting application.")
        return
    if not topic_choice:
        print("[TTS] I did'nt catch that, we will review weakest topics.")
    topic = flashcards.pick_topic(topic_choice)
    print(f"[TTS] Studying {topic}. I'll show you flashcards one by one.")

    while True:
        # 1. First, present any due cards
        due_cards = flashcards.get_due_cards()
        if due_cards:
            for card in due_cards:
                # After each card ask if they want to continue
                interrupted = _review_flashcard(card,flashcards)
                if interrupted:
                    print("[TTS] Alright, back to study mode.")
                    return
                print("[TTS] Do you want another flashcard?")
                cont = input("[STT] speak: ")
                cont = normalizeText(cont)
                if not cont or cont in NO_MORE_QUESTIONS_RESPONSES:
                    print("[TTS] Great work! Returning to study mode.")
                    return
                if cont in EXIT_APPLICATION_COMMANDS:
                    print("[TTS] Great work! Exiting application.")
                    should_stop_application = True
                    return
                print("[TTS] Alright, Next Card.")
            continue   # loop again to check for more due cards

        print("[DEBUG] here the new flashcard")        
        # 2. No due cards then generate a new one
        print("[TTS] Here's a new flashcard.")
        new_card = flashcards.generate_flashcard(topic)
        # Ask for continuation
        interrupted = _review_flashcard(new_card,flashcards)
        if interrupted:
            print("[TTS] Alright, back to study mode.")
            return
        print("[TTS] Another flashcard?")
        resp = input("[STT] speak: ")
        resp = normalizeText(resp)
        if not resp or resp in NO_MORE_QUESTIONS_RESPONSES:
            print("[TTS] Keep it up! Returning to study mode.")
            return
        if resp in EXIT_APPLICATION_COMMANDS:
            print("[TTS] Great work! Exiting application.")
            should_stop_application = True
            return
        print("[TTS] Alright, Next Card.")
        # else continue loop

# helper for flashcard_loop
def _review_flashcard(card, flashcards) -> bool:
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
    
    # Wait for "show answer"
    print("[Flashcard] Waiting for 'show answer'...")
    while True:
        cmd = input("[STT] speak: ")
        cmd = normalizeText(cmd)
        if cmd in SHOW_ANSWER_COMMANDS:
            break
        if not cmd:
            print("[TTS] Okay, moving on.")
            return False   # treat as skip
        if cmd in EXIT_APPLICATION_COMMANDS:
             should_stop_application = True
             return True # interrupt    
        print("[TTS] Say 'show answer' when you're ready.")

    answer_text = f"Answer: {card['answer']}"
    print(f"[Flashcard] {answer_text}")
    #
    # display answer on lcd screen here (not yet implemented)
    #
    # Ask difficulty rating
    print("[TTS] How difficult was that? Easy, medium, or hard?")
    rating = input("[STT] speak: ")
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
    print(f"[TTS] {confirm_msg}")

    return False

def main():
    assistant = BioAssistant()
    weakness_tracker = WeaknessTracker()

    while True:

        question = input("Enter the tett")
        question = normalizeText(question)
        topic = extract_topic(question)
        if topic:
            # quiz mode with specific topic
            quiz_loop(assistant, weakness_tracker=weakness_tracker, topic=topic)
            print("[MAIN] exited quiz with topic: {topic}")
                    
        if question in QUIZ_START_COMMANDS:
            quiz_loop(assistant, weakness_tracker=weakness_tracker)
            print("[MAIN] exited quiz with random topic")
        if question in FLASHCARD_START_COMMANDS:
            flashcard_loop(assistant, weakness_tracker)
            print("[MAIN] exited flashcard mode")   
            
            
if __name__ == "__main__":
    main()