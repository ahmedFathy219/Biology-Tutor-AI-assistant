# scripts/testBuzzer.py

import sys
import time
from pathlib import Path

from dotenv import load_dotenv


sys.path.append(
    str(
        Path(__file__).resolve().parents[1]
        / "src"
    )
)


from alerts import getBuzzerController


def main() -> None:

    load_dotenv()

    print(
        "[Buzzer Test] Initializing..."
    )


    buzzer = getBuzzerController()


    try:

        print(
            "[Buzzer Test] "
            "Starting repeating alert."
        )


        buzzer.alert()


        # Simulate student being distracted
        # for 8 seconds.
        time.sleep(8)


        print(
            "[Buzzer Test] "
            "Student focused again."
        )


        buzzer.stop()


        # Give us time to hear that it stopped.
        time.sleep(2)


    finally:

        buzzer.close()

        print(
            "[Buzzer Test] Finished."
        )


if __name__ == "__main__":
    main()