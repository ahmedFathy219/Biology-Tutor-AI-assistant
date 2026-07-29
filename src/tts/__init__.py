from .tts_engine import TTSEngine


def getTTSEngine():
    """
    Return a configured TTS engine.
    """
    return TTSEngine()