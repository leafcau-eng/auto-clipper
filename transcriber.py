import os
import json
import whisper
from config import CACHE_DIR

model = None

def load_model():
    global model
    if model is None:
        print(f"[TRANSCRIBER] Loading Whisper model: small")
        model = whisper.load_model("small")
    return model

def transcribe_candidates(video_path: str, candidates: list) -> list:
    m = load_model()
    audio_path = video_path.replace("downloads/", f"{CACHE_DIR}").replace(".mp4", ".wav")

    results = []
    for i, candidate in enumerate(candidates):
        cache_file = f"{CACHE_DIR}transcripts/candidate_{i}.json"
        os.makedirs(f"{CACHE_DIR}transcripts", exist_ok=True)

        if os.path.exists(cache_file):
            print(f"[TRANSCRIBER] Cache hit: candidate {i}")
            with open(cache_file) as f:
                transcript = json.load(f)
        else:
            print(f"[TRANSCRIBER] Transcribing candidate {i+1}/{len(candidates)}...")
            # Extract segment audio dulu - timestamp mulai dari 0
            segment_audio = _extract_segment(
                audio_path,
                candidate["start"],
                candidate["end"],
                i
            )
            # Transcribe segment yang udah di-extract
            # Timestamp otomatis mulai dari 0 karena audio udah dipotong
            transcript = m.transcribe(
                segment_audio,
                word_timestamps=True,
                language=None  # auto detect
            )

            with open(cache_file, "w") as f:
                json.dump(transcript, f, ensure_ascii=False, indent=2)

        candidate["transcript"]        = transcript["text"].strip()
        candidate["language"]          = transcript.get("language", "id")
        candidate["whisper_segments"]  = transcript.get("segments", [])
        # Set clip_start ke 0 karena audio udah dipotong per segment
        candidate["clip_offset"]       = 0
        results.append(candidate)

    print(f"[TRANSCRIBER] Done: {len(results)} candidates transcribed")
    return results

def _extract_segment(audio_path: str, start: float, end: float, idx: int) -> str:
    out_path = f"{CACHE_DIR}transcripts/seg_{idx}.wav"
    duration = end - start
    os.system(
        f'ffmpeg -i "{audio_path}" -ss {start:.2f} -t {duration:.2f} '
        f'"{out_path}" -y -loglevel error'
    )
    return out_path
