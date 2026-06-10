import os
import numpy as np
import librosa
from config import (
    DOWNLOAD_DIR, CACHE_DIR,
    TARGET_CANDIDATES,
    MIN_CLIP_DURATION,
    MAX_CLIP_DURATION
)

def find_candidates(video_path: str) -> list:
    audio_path = _extract_audio(video_path)
    y, sr = librosa.load(audio_path, sr=16000, mono=True)
    duration = len(y) / sr

    print(f"[CANDIDATE] Audio duration: {duration:.1f}s")

    # Bagi video jadi segmen langsung
    candidates = _split_into_segments(duration)
    print(f"[CANDIDATE] Found {len(candidates)} candidates")
    return candidates

def _extract_audio(video_path: str) -> str:
    os.makedirs(CACHE_DIR, exist_ok=True)
    video_id = os.path.basename(video_path).replace(".mp4", "")
    audio_path = f"{CACHE_DIR}{video_id}.wav"
    if not os.path.exists(audio_path):
        os.system(f'ffmpeg -i "{video_path}" -ar 16000 -ac 1 "{audio_path}" -y -loglevel error')
    print(f"[CANDIDATE] Audio extracted: {audio_path}")
    return audio_path

def _split_into_segments(duration: float) -> list:
    segments = []
    step = MIN_CLIP_DURATION
    start = 0.0

    while start + MIN_CLIP_DURATION <= duration and len(segments) < TARGET_CANDIDATES:
        end = min(start + MAX_CLIP_DURATION, duration)
        segments.append({
            "start": start,
            "end": end,
            "score_energy": 1.0,
            "score_pause": 1.0,
            "score_density": 1.0
        })
        start += step

    return segments
