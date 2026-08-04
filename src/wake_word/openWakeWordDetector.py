# src/wake_word/openwakeword_detector.py

import time

import pyaudio
import numpy as np
from scipy.signal import resample
from openwakeword.model import Model


class OpenWakeWordDetector:
    """
    Real wake word detector using OpenWakeWord.
    """

    TARGET_RATE = 16000
    CHUNK_DURATION = 0.08

    def __init__(
        self,
        model_name: str = "hey_jarvis",
        sensitivity: float = 0.4,
        device_index: int = None,
    ):
        """
        model_name:
            Name of the wake-word model.

        sensitivity:
            Detection threshold from 0 to 1.
            Lower = more sensitive.

        device_index:
            Microphone device index.
        """

        self.model = Model(
            wakeword_models=[model_name],
            inference_framework="onnx",
        )

        self.device_index = device_index

        self.pa = pyaudio.PyAudio()

        # Determine the supported microphone rate.
        self.input_rate = self._get_supported_rate(
            device_index
        )

        # Calculate chunk size dynamically.
        self.chunk_size = int(
            self.CHUNK_DURATION * self.input_rate
        )

        self.target_samples = int(
            self.TARGET_RATE * self.CHUNK_DURATION
        )

        self.stream = self.pa.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.input_rate,
            input=True,
            frames_per_buffer=self.chunk_size,
            input_device_index=self.device_index,
        )

        self.sensitivity = sensitivity

    def _get_supported_rate(self, device_index):
        """Return a sample rate the device can actually capture."""

        for rate in (16000, 48000, 44100):

            try:
                self.pa.is_format_supported(
                    rate,
                    input_device=device_index,
                    input_channels=1,
                    input_format=pyaudio.paInt16,
                )

                return rate

            except ValueError:
                continue

        # Fallback to device default.
        info = self.pa.get_device_info_by_index(
            device_index
            if device_index is not None
            else self.pa.get_default_input_device_info()["index"]
        )

        return int(info["defaultSampleRate"])

    def clearBuffer(self):
        """Clear previous wake-word detection state."""

        self.model.reset()

    def stop(self):
        """Release the microphone."""

        if self.stream is not None:

            if self.stream.is_active():
                self.stream.stop_stream()

            self.stream.close()
            self.stream = None

    def start(self):
        """Re-open the microphone for wake-word detection."""

        # Don't open a second stream if one already exists.
        if self.stream is not None:
            return

        self.stream = self.pa.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.input_rate,
            input=True,
            frames_per_buffer=self.chunk_size,
            input_device_index=self.device_index,
        )

        self.clearBuffer()

    def listenWakeWord(self, stop_event=None) -> bool:
        """
        Listen for the wake word.

        Returns True if the wake word is detected.

        Returns False if stop_event is set before
        the wake word is detected.
        """

        print(
            "[OpenWakeWord] Listening for wake word..."
        )

        while True:

            # --------------------------------------------------
            # Check whether another thread requested a stop.
            # --------------------------------------------------

            if (
                stop_event is not None
                and stop_event.is_set()
            ):
                return False

            # --------------------------------------------------
            # Make sure the microphone stream is available.
            # --------------------------------------------------

            if (
                self.stream is None
                or not self.stream.is_active()
            ):
                self.start()

            # --------------------------------------------------
            # Read microphone audio.
            # --------------------------------------------------

            pcm = self.stream.read(
                self.chunk_size,
                exception_on_overflow=False,
            )

            audio = np.frombuffer(
                pcm,
                dtype=np.int16,
            )

            # --------------------------------------------------
            # Resample to 16 kHz if necessary.
            # --------------------------------------------------

            if self.input_rate != self.TARGET_RATE:

                audio = resample(
                    audio,
                    self.target_samples,
                ).astype(np.int16)

            # --------------------------------------------------
            # Run OpenWakeWord.
            # --------------------------------------------------

            predictions = self.model.predict(audio)

            # --------------------------------------------------
            # Check wake-word confidence.
            # --------------------------------------------------

            for model_name, prob in predictions.items():

                if prob >= self.sensitivity:

                    print(
                        f"[OpenWakeWord] Detected "
                        f"'{model_name}' "
                        f"with confidence "
                        f"{prob:.2f}"
                    )

                    return True

            # Small delay to reduce CPU usage.
            time.sleep(0.01)

    def __del__(self):

        try:

            if self.stream is not None:
                self.stream.close()

            if self.pa is not None:
                self.pa.terminate()

        except Exception:
            pass