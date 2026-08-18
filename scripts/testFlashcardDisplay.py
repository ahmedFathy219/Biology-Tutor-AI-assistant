import sys
import time
from pathlib import Path

sys.path.append(
    str(
        Path(__file__).resolve().parents[1]
        / "src"
    )
)

from display import TftDisplay


def main():
    display = TftDisplay()
    display.start()

    try:
        display.showFlashcardTopics(
            [
                "Cell Biology",
                "Anatomy",
                "Genetics",
                "Ecology",
                "Evolution",
                "Photosynthesis",
                "Respiration",
                "DNA",
            ]
        )
        time.sleep(4)

        display.showFlashcardMode(
            "Cell Biology"
        )
        time.sleep(3)

        display.showFlashcardQuestion(
            "Cell Biology",
            "Which organelle produces most of the cell's ATP?",
        )
        time.sleep(4)

        display.showFlashcardAnswer(
            "Cell Biology",
            "The mitochondrion produces most of the cell's ATP.",
        )
        time.sleep(4)

        display.showFlashcardDifficulty(
            "Cell Biology"
        )
        time.sleep(4)

        display.showFlashcardMessage(
            "Marked as easy. It'll appear again later.",
            "Cell Biology",
        )
        time.sleep(4)

        display.showFlashcardMessage(
            "Another flashcard?",
            "Cell Biology",
        )
        time.sleep(4)

    finally:
        display.close()


if __name__ == "__main__":
    main()