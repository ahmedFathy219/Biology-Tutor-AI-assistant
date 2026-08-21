# src/stt/fasterWhisperSTT.py

from __future__ import annotations

from collections import deque
from typing import Optional

import numpy as np
import pyaudio
from scipy.signal import resample_poly
from faster_whisper import WhisperModel, audio


class FasterWhisperSTT:
    """
    Records one spoken command from the microphone and transcribes it
    using Faster-Whisper.
    """

    TARGET_RATE = 16000
    CHANNELS = 1
    CHUNK = 2048
    AUDIO_FORMAT = pyaudio.paInt16
    def __init__(
        self,
        model_size: str = "base.en",
        device: str = "cpu",
        compute_type: str = "int8",
        language: Optional[str] = "en",
        device_index: Optional[int] = None,
        speech_threshold: float = 400.0,
        silence_seconds: float = 1.5,
        wait_for_speech_seconds: float = 5.0,
        max_recording_seconds: float = 15.0,
        beam_size: int = 3,
        speech_vad_factor: float = 4.5,          # factor for std in speech detection
        silence_vad_factor: float = 2.0,          # factor for std in silence detection
    ) -> None:
        self.device_index = device_index
        self.language = language
        self.speech_threshold = speech_threshold
        self.silence_seconds = silence_seconds
        self.wait_for_speech_seconds = wait_for_speech_seconds
        self.max_recording_seconds = max_recording_seconds
        self.beam_size = beam_size
        self.speech_vad_factor = speech_vad_factor
        self.silence_vad_factor = silence_vad_factor
        #determine a working input rate
        pa = pyaudio.PyAudio()
        self.input_rate = self._get_supported_rate(pa)
        pa.terminate()

        print(
            f"[STT] Loading Whisper model: {model_size} "
            f"(device={device}, compute_type={compute_type})"
        )

        self.model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type,
        )

        print("[STT] Whisper model loaded successfully.")

    def _get_supported_rate(self, pa):
        for rate in (16000, 48000, 44100):
            try:
                pa.is_format_supported(
                    rate,
                    input_device=self.device_index,
                    input_channels=1,
                    input_format=pyaudio.paInt16
                )
                return rate
            except ValueError:
                continue
        info = pa.get_device_info_by_index(
            self.device_index if self.device_index is not None
            else pa.get_default_input_device_info()['index']
        )
        return int(info['defaultSampleRate'])        
    @staticmethod
    def _calculate_rms(data: bytes) -> float:
        """
        Calculate the RMS audio level.

        A higher RMS value generally means louder audio.
        """

        samples = np.frombuffer(data, dtype=np.int16)

        if samples.size == 0:
            return 0.0

        float_samples = samples.astype(np.float32)

        return float(
            np.sqrt(np.mean(float_samples * float_samples))
        )

    def recordCommand(
         self,
         wait_for_speech_seconds: Optional[float] = None,
    ) -> np.ndarray:
        """
        Wait for speech, record until silence, and return normalized
        audio as a float32 NumPy array.
        """

        audio_manager = pyaudio.PyAudio()
        stream = None

        try:
            if self.device_index is None:
                device_info = (
                    audio_manager.get_default_input_device_info()
                )
                selected_device_index = int(device_info["index"])
            else:
                selected_device_index = self.device_index
                device_info = audio_manager.get_device_info_by_index(
                    selected_device_index
                )

            print(
                f"[STT] Using microphone index "
                f"{selected_device_index}: {device_info['name']}"
            )

            stream = audio_manager.open(
                format=self.AUDIO_FORMAT,
                channels=self.CHANNELS,
                rate=self.input_rate,
                input=True,
                input_device_index=selected_device_index,
                frames_per_buffer=self.CHUNK,
            )

            #discard initial noisy samples, removes startup glitch when sample rate > 16kHz
            self.warmup_seconds = 0.5
            warmup_chunks = max(1, int(self.warmup_seconds * self.input_rate / self.CHUNK))
            for _ in range(warmup_chunks):
                stream.read(
                    self.CHUNK,
                    exception_on_overflow=False
                )

            # 1. Collect baseline RMS from first 0.5 seconds of quiet
            baseline_chunks = int(0.5 * self.input_rate / self.CHUNK)
            baseline_rms_values = []
            for _ in range(baseline_chunks):
                data = stream.read(self.CHUNK, exception_on_overflow=False)
                rms = self._calculate_rms(data)
                baseline_rms_values.append(rms)
            mean_rms = np.mean(baseline_rms_values)
            std_rms = max(np.std(baseline_rms_values), 1.0)

            speech_threshold = mean_rms + self.speech_vad_factor * std_rms

            silence_threshold = mean_rms + self.silence_vad_factor * std_rms

            print(f"[STT] Noise: mean={mean_rms:.1f}, std={std_rms:.1f}")
            print(f"[STT] Speech threshold = {speech_threshold:.1f}, Silence threshold = {silence_threshold:.1f}")

            # Avoid division by zero or too-low baseline
            if mean_rms < 1.0:
                mean_rms = 1.0

            # Detection thresholds (tune these factors)


            print("[STT] Listening for your question...")

            # Keep a small amount of audio from immediately before
            # speech is detected. This avoids cutting off the first word.

            pre_roll_seconds = 1
            pre_roll_chunks = max(
                1.0,
                int(pre_roll_seconds * self.input_rate / self.CHUNK),
            )
            pre_roll: deque[bytes] = deque(
                maxlen=pre_roll_chunks
            )

            frames: list[bytes] = []

            speech_started = False
            silence_chunk_count = 0
            waiting_chunk_count = 0
            recorded_chunk_count = 0

            actual_wait_seconds= (
                self.wait_for_speech_seconds
                if wait_for_speech_seconds is None
                else wait_for_speech_seconds
            )

            wait_limit = max(
                1,
                int(
                    actual_wait_seconds
                    * self.input_rate
                    / self.CHUNK
                ),
            )

            silence_limit = max(
                1,
                int(
                    self.silence_seconds
                    * self.input_rate
                    / self.CHUNK
                ),
            )

            recording_limit = max(
                1,
                int(
                    self.max_recording_seconds
                    * self.input_rate
                    / self.CHUNK
                ),
            )

            while True:
                data = stream.read(
                    self.CHUNK,
                    exception_on_overflow=False,
                )

                rms = self._calculate_rms(data)
                if not speech_started:
                    pre_roll.append(data)
                    waiting_chunk_count += 1

                    if rms >= speech_threshold:
                        speech_started = True
                        frames.extend(pre_roll)

                        print(
                            f"[STT] Speech detected "
                            f"(level={rms:.1f})."
                        )

                    elif waiting_chunk_count >= wait_limit:
                        print(
                            "[STT] No speech was detected before "
                            "the timeout."
                        )

                        return np.array([], dtype=np.float32)

                    continue

                frames.append(data)
                recorded_chunk_count += 1

                if rms < silence_threshold:
                    silence_chunk_count += 1
                else:
                    silence_chunk_count = 0

                if silence_chunk_count >= silence_limit:
                    print("[STT] End of speech detected.")
                    break

                if recorded_chunk_count >= recording_limit:
                    print(
                        "[STT] Maximum recording duration reached."
                    )
                    break

            raw_audio = b"".join(frames)

            int16_audio = np.frombuffer(
                raw_audio,
                dtype=np.int16,
            )

            # Resample entire recording to 16 kHz with SciPy
            if self.input_rate != self.TARGET_RATE:
                # resample_poly with rational conversion
                int16_audio = resample_poly(
                    int16_audio.astype(np.float64),
                    self.TARGET_RATE,
                    self.input_rate
                ).astype(np.int16)
            
            # Whisper expects float audio approximately between -1 and 1.
            normalized_audio = (
                int16_audio.astype(np.float32) / 32768.0
            )

            return normalized_audio

        finally:
            if stream is not None:
                if stream.is_active():
                    stream.stop_stream()

                stream.close()

            audio_manager.terminate()

    def transcribeAudio(self, audio: np.ndarray) -> str:
        """
        Convert a recorded NumPy audio array into text.
        """

        if audio.size == 0:
            return ""

        print("[STT] Transcribing...")

        segments, information = self.model.transcribe(
            audio,
            language=self.language,
            task="transcribe",
            beam_size=self.beam_size,
            vad_filter=True,
            vad_parameters={
                "min_silence_duration_ms": 400,
            },
            condition_on_previous_text=False
        )

        # Faster-Whisper returns segments as a generator.
        # Iterating through it performs the actual transcription.
        transcript_parts = [
            segment.text.strip()
            for segment in segments
            if segment.text.strip()
        ]

        transcript = " ".join(transcript_parts).strip()

        if transcript:
            print(
                f"[STT] Detected language: "
                f"{information.language}"
            )
        else:
            print("[STT] No understandable speech was found.")

        return transcript

    def listenAndTranscribe(
        self,
        wait_for_speech_seconds: Optional[float] = None,
    ) -> str:
        """
        Record and transcribe one spoken command.

        A temporary timeout can be supplied for short follow-up windows.
        """

        audio = self.recordCommand(
            wait_for_speech_seconds=wait_for_speech_seconds
        )

        return self.transcribeAudio(audio)