# src/wake_word/__init__.py
import os
from .openWakeWordDetector import OpenWakeWordDetector

def getWakeWordDetector() -> OpenWakeWordDetector:
    
    model_name = os.environ.get("OWW_MODEL", "hey_jarvis")
    print(model_name)
    sensitivity = float(os.environ.get("OWW_SENSITIVITY", "0.5"))

    device_index_str = os.environ.get("MIC_DEVICE_INDEX")
    device_index = int(device_index_str) if device_index_str is not None else None

    print(f"[WakeWord] Using OpenWakeWord model: {model_name} (sensitivity={sensitivity})")
    if device_index is not None:
        print(f"[WakeWord] Using audio input device index: {device_index}")

    return OpenWakeWordDetector(model_name=model_name, sensitivity=sensitivity, device_index=device_index)