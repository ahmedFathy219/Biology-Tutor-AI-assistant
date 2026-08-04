import sys
import time
import threading
from pathlib import Path

sys.path.append(
    str(
        Path(__file__).resolve().parents[1]
        / "src"
    )
)

from tts import getTTSEngine
from wake_word import getWakeWordDetector


def main():

    print("[Test] Initializing components...")

    tts = getTTSEngine()
    wake_word = getWakeWordDetector()

    print("[Test] Components ready.")

    long_text = (
        "Hello, I am Echo. "
        "I am going to explain something about biology. "
        "This is intentionally a long response so that "
        "you have enough time to interrupt me. "
        "While I am speaking, say Hey Echo. "
        "The wake word detector should hear you and "
        "immediately stop my speech. "
        "After that, we will connect this system to "
        "the main Study Buddy application."
    )

    def speak():
        print("[Test] Echo started speaking.")
        tts.speak(long_text)
        print("[Test] Echo finished speaking.")

    speech_thread = threading.Thread(
        target=speak
    )

    speech_thread.start()

    print()
    print("[Test] Say 'Hey Echo' while Echo is speaking.")
    print("[Test] Waiting for interruption...")
    print()

    # Keep listening for the wake word while TTS speaks.
    wake_word.listenWakeWord()

    print("[Test] Wake word detected!")
    print("[Test] Interrupting Echo...")

    tts.stop()

    speech_thread.join()

    print("[Test] Echo has been interrupted.")

    wake_word.stop()

    print("[Test] Test finished.")


if __name__ == "__main__":
    main()