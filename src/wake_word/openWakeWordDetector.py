# src/wake_word/openwakeword_detector.py
import time
import pyaudio
import numpy as np
from scipy.signal import resample
from openwakeword.model import Model

class OpenWakeWordDetector():
    """
    Real wake word detector using OpenWakeWord.
    Uses a pre-trained 'hey_jarvis' model that comes with the library.
    """

    TARGET_RATE = 16000
    CHUNK_DURATION = 0.08

    def __init__(self, model_name: str = "hey_jarvis", sensitivity: float = 0.5, device_index: int = None):
        """
        model_name: name of the built-in model, default is hey_jarvis which is built into openWakeWord lib
        sensitivity: detection threshold (0-1), lower = more sensitive.
        device_index: determines which microphone to listen on, find device index by running "python scripts/listInputDevices.py" 
        """
        self.model = Model(wakeword_models=[model_name], inference_framework="onnx")

        self.device_index = device_index
        
        self.pa = pyaudio.PyAudio()

        #determine the input device rate depending on the device
        self.input_rate = self._get_supported_rate(device_index)

        #dynamically calculate chunksize
        self.chunk_size = int(self.CHUNK_DURATION * self.input_rate)

        self.target_samples = int(self.TARGET_RATE * self.CHUNK_DURATION)
        
        self.stream = self.pa.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.input_rate,
            input=True,
            frames_per_buffer=self.chunk_size,
            input_device_index=self.device_index
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
                    input_format=pyaudio.paInt16
                )
                return rate
            except ValueError:
                continue
        # Fallback to device default
        info = self.pa.get_device_info_by_index(
            device_index if device_index is not None
            else self.pa.get_default_input_device_info()['index']
        )
        return int(info['defaultSampleRate'])
    
    def clearBuffer(self):
        #clear buffer to prevent repeated detections
        self.model.reset()

    def stop(self):
        """Release the microphone so other components can use it."""
        if self.stream.is_active():
            self.stream.stop_stream()
        self.stream.close()

    def start(self):
        """Re-open the stream to resume listening for the wake word."""
        self.stream = self.pa.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.input_rate,
            input=True,
            frames_per_buffer=self.chunk_size,
            input_device_index=self.device_index
        )
        self.clearBuffer()

    def listenWakeWord(self) -> bool:
        """
        Keeps listening in a loop until the wake word is detected.
        Returns True once detection probability exceeds sensitivy value.
        """
        print(f"[OpenWakeWord] Listening for wake word...")
        while True:

            #Ensure stream is open before reading
            if not self.stream or not self.stream.is_active():
                self.start()

            # Read a small chunk of audio
            pcm = self.stream.read(self.chunk_size, exception_on_overflow=False)
            audio = np.frombuffer(pcm, dtype=np.int16)

            # If not 16 kHz, resample with SciPy
            if self.input_rate != self.TARGET_RATE:
                audio = resample(audio,self.target_samples).astype(np.int16)
                
            # Predict (returns a dict with model_name: probability)
            predictions = self.model.predict(audio)

            # Check if the wake word exceeds sensitivity
            for model_name, prob in predictions.items():
                if prob >= self.sensitivity:
                    print(f"[OpenWakeWord] Detected '{model_name}' with confidence {prob:.2f}")
                    return True

            # short delay, to prevent high cpu utilization
            time.sleep(0.01)

    def __del__(self):
        try:
            self.stream.close()
            self.pa.terminate()
        except:
            pass