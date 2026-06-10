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

    print("[CANDIDATE] Analyzing audio...")
    energy_segments   = _detect_energy(y, sr)
    pause_segments    = _detect_pauses(y, sr)
    density_segments  = _detect_speech_density(y, sr)

    candidates = _merge_segments(energy_segments, pause_segments, density_segments, y, sr)
    candidates = _filter_duration(candidates)
    candidates = _sort_and_limit(candidates)

    print(f"[CANDIDATE] Found {len(candidates)} candidates")
    return candidates

def _extract_audio(video_path: str) -> str:
    os.makedirs(CACHE_DIR, exist_ok=True)
    audio_path = video_path.replace(DOWNLOAD_DIR, f"{CACHE_DIR}").replace(".mp4", ".wav")
    if not os.path.exists(audio_path):
        os.system(f'ffmpeg -i "{video_path}" -ar 16000 -ac 1 "{audio_path}" -y -loglevel error')
    print(f"[CANDIDATE] Audio extracted: {audio_path}")
    return audio_path

def _detect_energy(y, sr) -> list:
    hop_length = 512
    frame_energy = librosa.feature.rms(y=y, hop_length=hop_length)[0]
    threshold = np.mean(frame_energy) * 1.5
    times = librosa.frames_to_time(range(len(frame_energy)), sr=sr, hop_length=hop_length)

    segments = []
    start = None
    for i, e in enumerate(frame_energy):
        if e > threshold and start is None:
            start = times[i]
        elif e <= threshold and start is not None:
            segments.append({"start": start, "end": times[i], "score_energy": float(np.mean(frame_energy))})
            start = None
    return segments

def _detect_pauses(y, sr) -> list:
    intervals = librosa.effects.split(y, top_db=30)
    segments = []
    for start, end in intervals:
        t_start = start / sr
        t_end   = end / sr
        duration = t_end - t_start
        if duration >= MIN_CLIP_DURATION:
            segments.append({"start": t_start, "end": t_end, "score_pause": duration})
    return segments

def _detect_speech_density(y, sr) -> list:
    hop_length = 512
    zcr = librosa.feature.zero_crossing_rate(y, hop_length=hop_length)[0]
    times = librosa.frames_to_time(range(len(zcr)), sr=sr, hop_length=hop_length)
    threshold = np.mean(zcr) * 1.2

    segments = []
    start = None
    for i, z in enumerate(zcr):
        if z > threshold and start is None:
            start = times[i]
        elif z <= threshold and start is not None:
            segments.append({"start": start, "end": times[i], "score_density": float(np.mean(zcr))})
            start = None
    return segments

def _merge_segments(energy, pauses, density, y, sr) -> list:
    all_segments = energy + pauses + density
    if not all_segments:
        return []

    # Gabung berdasarkan overlap waktu
    all_segments.sort(key=lambda x: x["start"])
    merged = []
    for seg in all_segments:
        if merged and seg["start"] < merged[-1]["end"]:
            merged[-1]["end"] = max(merged[-1]["end"], seg["end"])
            merged[-1].update(seg)
        else:
            merged.append(dict(seg))
    return merged

def _filter_duration(segments: list) -> list:
    return [
        s for s in segments
        if MIN_CLIP_DURATION <= (s["end"] - s["start"]) <= MAX_CLIP_DURATION
    ]

def _sort_and_limit(segments: list) -> list:
    def score(s):
        return (
            s.get("score_energy", 0) +
            s.get("score_pause", 0) +
            s.get("score_density", 0)
        )
    segments.sort(key=score, reverse=True)
    return segments[:TARGET_CANDIDATES]
