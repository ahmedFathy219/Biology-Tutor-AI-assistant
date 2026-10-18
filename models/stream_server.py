import io
import struct
import wave

import numpy as np

from fastapi import FastAPI, Form
from fastapi.responses import StreamingResponse
import uvicorn

from pocket_tts import TTSModel


HOST = "127.0.0.1"
PORT = 8002

VOICE_FILE = r"E:\pocket-tts-test\attenborough-voice.safetensors"


print("[Pocket TTS] Loading model...")
model = TTSModel.load_model()

print("[Pocket TTS] Loading Attenborough voice...")
voice_state = model.get_state_for_audio_prompt(VOICE_FILE)

print("[Pocket TTS] Ready.")


app = FastAPI()


def tensor_to_wav_bytes(audio):
    audio_np = audio.detach().cpu().numpy()

    audio_np = np.clip(audio_np, -1.0, 1.0)

    audio_int16 = (audio_np * 32767).astype(np.int16)

    buffer = io.BytesIO()

    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(model.sample_rate)
        wav.writeframes(audio_int16.tobytes())

    return buffer.getvalue()


@app.get("/health")
def health():
    return {
        "status": "ok",
        "sample_rate": model.sample_rate,
        "streaming": True,
    }


@app.post("/tts-stream")
def tts_stream(text: str = Form(...)):

    def generate():

        for chunk in model.generate_audio_stream(
            voice_state,
            text,
        ):

            wav_bytes = tensor_to_wav_bytes(chunk)

            yield struct.pack(
                "!I",
                len(wav_bytes),
            )

            yield wav_bytes

    return StreamingResponse(
        generate(),
        media_type="application/octet-stream",
    )


if __name__ == "__main__":

    print(
        f"[Pocket TTS] Streaming server running at "
        f"http://{HOST}:{PORT}"
    )

    uvicorn.run(
        app,
        host=HOST,
        port=PORT,
    )