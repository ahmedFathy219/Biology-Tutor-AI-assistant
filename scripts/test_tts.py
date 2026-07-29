import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))

from tts import getTTSEngine

tts = getTTSEngine()
tts.speak("Hello Mohamed. I am Echo.")