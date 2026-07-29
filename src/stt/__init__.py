# src/stt/__init__.py

import os
from typing import Optional

from .fasterWhisperSTT import FasterWhisperSTT


def _getOptionalInteger(variable_name: str) -> Optional[int]:
    value = os.environ.get(variable_name)
import os
from typing import Optional

from .fasterWhisperSTT import FasterWhisperSTT


def getOptionalInteger(variable_name: str) -> Optional[int]:
    value = os.environ.get(variable_name)

    if value is None or value.strip() == "":
        return None

    try:
        return int(value)
    except ValueError as error:
        raise ValueError(
            f"{variable_name} must be an integer."
        ) from error


def getSpeechToText() -> FasterWhisperSTT:
    return FasterWhisperSTT(
        model_size=os.environ.get("STT_MODEL", "base.en"),
        device=os.environ.get("STT_DEVICE", "cpu"),
        compute_type=os.environ.get(
            "STT_COMPUTE_TYPE",
            "int8",
        ),
        language=os.environ.get("STT_LANGUAGE", "en"),
        device_index=getOptionalInteger(
            "MIC_DEVICE_INDEX"
        ),
        speech_threshold=float(
            os.environ.get("STT_SPEECH_THRESHOLD", "400")
        ),
        silence_seconds=float(
            os.environ.get("STT_SILENCE_SECONDS", "1.2")
        ),
        wait_for_speech_seconds=float(
            os.environ.get(
                "STT_WAIT_FOR_SPEECH_SECONDS",
                "5",
            )
        ),
        max_recording_seconds=float(
            os.environ.get(
                "STT_MAX_RECORDING_SECONDS",
                "15",
            )
        ),
        beam_size=int(
            os.environ.get("STT_BEAM_SIZE", "3")
        ),
    )
    if value is None or value.strip() == "":
        return None

    try:
        return int(value)
    except ValueError as error:
        raise ValueError(
            f"{variable_name} must be an integer."
        ) from error


def getSpeechToText() -> FasterWhisperSTT:
    return FasterWhisperSTT(
        model_size=os.environ.get(
            "STT_MODEL",
            "base.en",
        ),
        device=os.environ.get(
            "STT_DEVICE",
            "cpu",
        ),
        compute_type=os.environ.get(
            "STT_COMPUTE_TYPE",
            "int8",
        ),
        language=os.environ.get(
            "STT_LANGUAGE",
            "en",
        ),
        device_index=_getOptionalInteger(
            "MIC_DEVICE_INDEX"
        ),
        speech_threshold=float(
            os.environ.get(
                "STT_SPEECH_THRESHOLD",
                "400",
            )
        ),
        silence_seconds=float(
            os.environ.get(
                "STT_SILENCE_SECONDS",
                "1.2",
            )
        ),
        wait_for_speech_seconds=float(
            os.environ.get(
                "STT_WAIT_FOR_SPEECH_SECONDS",
                "5",
            )
        ),
        max_recording_seconds=float(
            os.environ.get(
                "STT_MAX_RECORDING_SECONDS",
                "15",
            )
        ),
        beam_size=int(
            os.environ.get(
                "STT_BEAM_SIZE",
                "3",
            )
        ),
    )