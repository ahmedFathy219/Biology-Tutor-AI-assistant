import time


from src.display import TftDisplay


def main():

    print("[Display Test] Starting Echo display...")

    display = TftDisplay()

    display.start()

    display.showWakeGuide()

    print("[Display Test] Display is running.")
    print("[Display Test] Press Ctrl+C to stop.")

    try:

        while True:
            time.sleep(1)

    except KeyboardInterrupt:

        print("\n[Display Test] Closing display...")

        display.close()

        print("[Display Test] Done.")


if __name__ == "__main__":
    main()