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

    print("[Buzzer Test] Initializing...")

    buzzer = getBuzzerController()

    try:
        print("[Buzzer Test] Starting alert.")

        alert_started = buzzer.alert()

        if alert_started:
            print("[Buzzer Test] Alert successfully triggered.")
        else:
            print("[Buzzer Test] Alert blocked by cooldown.")

        # The hardware beep pattern runs in the background,
        # so wait before closing the GPIO resource.
        time.sleep(6)

    finally:
        buzzer.close()
        print("[Buzzer Test] Finished.")


if __name__ == "__main__":
    main()