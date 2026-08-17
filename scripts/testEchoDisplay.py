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

        print("Wake guide")
        display.showWakeGuide()
        time.sleep(3)

        print("Listening")
        display.showListening()
        time.sleep(3)

        print("Thinking")
        display.showThinking()
        time.sleep(3)

        print("Answering")
        display.showAnswering(
            "Cells are the basic\nunits of life.",
            1,
            2,
        )
        time.sleep(4)

        print("Attention warning")
        display.showAttentionWarning()
        time.sleep(3)

        print("Restoring")
        display.clearAttentionWarning()
        time.sleep(3)

    finally:

        display.close()


if __name__ == "__main__":
    main()