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
        display.showQuizTopics(
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
        time.sleep(3)

        display.showQuizTime("Cell Biology")
        time.sleep(3)

        display.showQuizQuestion(
            1,
            "Cell Biology",
            "Which organelle is responsible for producing most of the cell's ATP?",
        )
        time.sleep(4)

        display.showQuizResult(
            True,
            3,
            "Great job! Mitochondria generate most of the cell's ATP.",
        )
        time.sleep(4)

        display.showQuizMessage(
            "Would you like another question?",
            3,
        )
        time.sleep(4)

        display.showQuizResult(
            False,
            0,
            "Not quite. Review the organelle responsible for cellular energy production.",
        )
        time.sleep(4)

    finally:
        display.close()


if __name__ == "__main__":
    main()
