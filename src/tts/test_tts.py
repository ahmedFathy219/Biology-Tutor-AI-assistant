#!/usr/bin/env python3
"""
Simple test script for LocalTTSEngine.
Measures performance and plays audio so you can judge voice quality.
"""

import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # project root
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

# Optional: for resource monitoring
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

# Import your TTS engine – adjust path if needed
from tts.local_tts_engine import LocalTTSEngine


def print_resources():
    """Print CPU and memory usage if psutil is available."""
    if HAS_PSUTIL:
        cpu = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        print(f"CPU usage: {cpu}% | RAM used: {mem.used / 1024**3:.2f} GB / {mem.total / 1024**3:.2f} GB")
    else:
        print("Install psutil for resource monitoring: pip install psutil")


def run_test(engine, text, description):
    """Speak a text and measure time."""
    print(f"\n--- {description} ---")
    print(f"Text: {text}")
    if HAS_PSUTIL:
        print_resources()

    start = time.time()
    engine.speak(text)
    end = time.time()

    # Wait a moment for the engine to finish (it may still be playing)
    # But speak() is blocking, so we are done.
    print(f"Time taken: {end - start:.2f} seconds")


def interactive_mode(engine):
    """Allow user to type text repeatedly."""
    print("\n--- Interactive Mode ---")
    print("Type a sentence and press Enter to hear it.")
    print("Type 'quit' or 'exit' to stop.")
    while True:
        text = input("\nYou: ").strip()
        if text.lower() in ("quit", "exit"):
            break
        if not text:
            continue
        run_test(engine, text, "User input")


def main():
    # You can pass a custom model path here if you have one
    # model_path = "/path/to/your/model.onnx"
    # engine = LocalTTSEngine(voice_model=model_path)
    engine = LocalTTSEngine()  # uses default downloaded model

    print("\n=== Local TTS Engine Test ===")
    print("Make sure your speakers/headphones are connected.")
    input("Press Enter to start the test...")

    # Test sentences with different punctuation for tone variation
    test_cases = [
        ("The quick brown fox jumps over the lazy dog.", "Statement"),
        ("Is this a question that I hear?", "Question"),
        ("Wow! This is absolutely fantastic!", "Exclamation"),
        ("David Attenborough style narration: the penguins march across the ice.", "Narration"),
    ]

    for text, desc in test_cases:
        run_test(engine, text, desc)

    # Optional interactive mode
    choice = input("\nDo you want to test your own text? (y/n): ").strip().lower()
    if choice.startswith("y"):
        interactive_mode(engine)

    print("\nTest finished. Goodbye!")


if __name__ == "__main__":
    main()