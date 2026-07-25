# list_devices.py
import pyaudio

p = pyaudio.PyAudio()
for i in range(p.get_device_count()):
    info = p.get_device_info_by_index(i)
    if info['maxInputChannels'] > 0:   # only input devices
        print(f"Index {i}: {info['name']} - {info['hostApi']}")
p.terminate()