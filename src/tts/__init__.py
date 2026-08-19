from .tts_engine import TTSEngine


def getTTSEngine(pause_event=None, resume_event=None):
    """
    Return a configured TTS engine.
    """
    return TTSEngine(pause_event, resume_event)