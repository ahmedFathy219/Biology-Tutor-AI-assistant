import pyaudio
import numpy as np

CHUNK = 1024
RATE = 16000

p = pyaudio.PyAudio()
# Find the default input device info
default_input = p.get_default_input_device_info()
print(f"Using: {default_input['name']}")

stream = p.open(format=pyaudio.paInt16,
                channels=1,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK,
                input_device_index=1)

print("Listening... (speak now, press Ctrl+C to stop)")
try:
    while True:
        data = stream.read(CHUNK, exception_on_overflow=False)
        # Calculate RMS (volume level)
        samples = np.frombuffer(data, dtype=np.int16)
        rms = np.sqrt(np.mean(samples.astype(np.float64)**2))
        bar = "#" * int(rms / 100)
        print(f"Mic level: {rms:8.1f} {bar}", end="\r")
except KeyboardInterrupt:
    print("\nDone.")
finally:
    stream.stop_stream()
    stream.close()
    p.terminate()