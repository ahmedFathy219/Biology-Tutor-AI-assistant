# src/stt/__init__.py

import os
from typing import Optional

from .fasterWhisperSTT import FasterWhisperSTT


def _get_optional_integer(variable_name: str) -> Optional[int]:
    """Return an integer from environment variable, or None if missing/invalid."""
    value = os.environ.get(variable_name)
    if value is None or value.strip() == "":
        return None
    try:
        return int(value)
    except ValueError as error:
        raise ValueError(f"{variable_name} must be an integer.") from error


def getSpeechToText() -> FasterWhisperSTT:
    """Create and return a FasterWhisperSTT instance configured from environment."""
    return FasterWhisperSTT(
        model_size=os.environ.get("STT_MODEL", "base.en"),
        device=os.environ.get("STT_DEVICE", "cpu"),
        compute_type=os.environ.get("STT_COMPUTE_TYPE", "int8"),
        language=os.environ.get("STT_LANGUAGE", "en"),
        device_index=_get_optional_integer("MIC_DEVICE_INDEX"),
        speech_threshold=float(os.environ.get("STT_SPEECH_THRESHOLD", "400")),
        silence_seconds=float(os.environ.get("STT_SILENCE_SECONDS", "1.2")),
        wait_for_speech_seconds=float(os.environ.get("STT_WAIT_FOR_SPEECH_SECONDS", "5")),
        max_recording_seconds=float(os.environ.get("STT_MAX_RECORDING_SECONDS", "15")),
        beam_size=int(os.environ.get("STT_BEAM_SIZE", "3")),
    )