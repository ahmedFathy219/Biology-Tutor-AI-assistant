import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from tts import getTTSEngine

tts = getTTSEngine()

text = """
**Photosynthesis**

- Uses sunlight
- Produces glucose

1. Light reaction
2. Calvin cycle
"""

print("Before cleaning:")
print(text)

print("\nAfter cleaning:")
print(tts.clean_text(text))

tts.speak(text)