from pocket_tts import TTSModel
import time

model = TTSModel.load_model()

voice_state = model.get_state_for_audio_prompt(
    r".\attenborough-voice.safetensors"
)

text = (
    "We have already discussed this earlier. To recap, one main difference "
    "between DNA and RNA is that DNA contains thymine, while RNA contains "
    "uracil instead. Additionally, DNA has deoxyribose sugars, whereas RNA "
    "has ribose sugars."
)

start = time.perf_counter()
first_chunk_time = None
total_samples = 0
chunk_count = 0

print("Starting Pocket TTS streaming test...")

for chunk in model.generate_audio_stream(
    voice_state,
    text,
):
    chunk_count += 1
    total_samples += chunk.shape[0]

    if first_chunk_time is None:
        first_chunk_time = time.perf_counter()

    elapsed = time.perf_counter() - start

    print(
        f"Chunk {chunk_count}: "
        f"{chunk.shape[0]} samples | "
        f"{elapsed:.2f}s elapsed"
    )

total_time = time.perf_counter() - start

print()
print(f"First chunk: {first_chunk_time - start:.2f}s")
print(f"Total chunks: {chunk_count}")
print(
    f"Audio duration: "
    f"{total_samples / model.sample_rate:.2f}s"
)
print(f"Total generation time: {total_time:.2f}s")
print(
    f"Real-time factor: "
    f"{total_time / (total_samples / model.sample_rate):.2f}x"
)