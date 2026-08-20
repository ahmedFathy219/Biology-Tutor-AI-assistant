import platform
from .tts_engine import TTSEngine
from .local_tts_engine import LocalTTSEngine

def getTTSEngine(pause_event=None, resume_event=None):
    """
    Return a TTS engine.
    On Raspberry Pi 5, use the local lightweight engine; otherwise use the original server-based one.
    """
    # Detect Raspberry Pi 5
    is_pi5 = False
    try:
        with open("/proc/device-tree/model", "r") as f:
            model = f.read().strip()
            if "Raspberry Pi 5" in model:
                is_pi5 = True
    except:
        pass

    if is_pi5:
        # Optionally pass a custom voice model path if you have one
        return LocalTTSEngine(pause_event=pause_event, resume_event=resume_event)
    else:
        return TTSEngine(pause_event, resume_event)