# scripts/download_openwakeword_models.py

from pathlib import Path

import openwakeword
from openwakeword.utils import download_models


REQUIRED_MODELS = (
    "melspectrogram.onnx",
    "embedding_model.onnx",
)


def get_models_directory() -> Path:
    """Return openWakeWord's internal resource-model directory."""
    return (
        Path(openwakeword.__file__).resolve().parent
        / "resources"
        / "models"
    )


def find_missing_models(models_directory: Path) -> list[str]:
    """Return the required ONNX models that are not installed."""
    return [
        model_name
        for model_name in REQUIRED_MODELS
        if not (models_directory / model_name).is_file()
    ]


def main() -> None:
    models_directory = get_models_directory()
    missing_models = find_missing_models(models_directory)

    if not missing_models:
        print("[Setup] openWakeWord resource models are already installed.")
        print(f"[Setup] Location: {models_directory}")
        return

    print("[Setup] Missing openWakeWord models:")

    for model_name in missing_models:
        print(f"  - {model_name}")

    print("[Setup] Downloading openWakeWord resources...")

    try:
        download_models()
    except Exception as error:
        raise RuntimeError(
            "Failed to download openWakeWord models. "
            "Check your internet connection and try again."
        ) from error

    still_missing = find_missing_models(models_directory)

    if still_missing:
        raise FileNotFoundError(
            "The following models are still missing after the download: "
            + ", ".join(still_missing)
        )

    print("[Setup] openWakeWord resource models downloaded successfully.")
    print(f"[Setup] Location: {models_directory}")


if __name__ == "__main__":
    main()