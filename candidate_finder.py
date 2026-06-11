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
    print(f"[CANDIDATE] Analyzing audio energy, pauses, speech density...")

    energy_segs  = _detect_energy(y, sr)
    pause_segs   = _detect_pauses(y, sr)
    density_segs = _detect_speech_density(y, sr)

    print(f"[CANDIDATE] Energy: {len(energy_segs)} | Pause: {len(pause_segs)} | Density: {len(density_segs)}")

    all_segs = energy_segs + pause_segs + density_segs
    merged   = _merge_segments(all_segs)
    filtered = _filter_duration(merged)
    top      = _sort_and_limit(filtered)

    # Fallback kalau ngga ketemu cukup kandidat
    if len(top) < 5:
        print(f"[CANDIDATE] Too few candidates ({len(top)}), adding fallback segments...")
        top += _fallback_segments(duration, existing=top)
        top = top[:TARGET_CANDIDATES]

    print(f"[CANDIDATE] Final candidates: {len(top)}")
    return top

def _extract_audio(video_path: str) -> str:
    os.makedirs(CACHE_DIR, exist_ok=True)
    video_id   = os.path.basename(video_path).replace(".mp4", "")
    audio_path = f"{CACHE_DIR}{video_id}.wav"
    if not os.path.exists(audio_path):
        os.system(f'ffmpeg -i "{video_path}" -ar 16000 -ac 1 "{audio_path}" -y -loglevel error')
    print(f"[CANDIDATE] Audio extracted: {audio_path}")
    return audio_path

def _detect_energy(y, sr) -> list:
    hop_length   = 512
    frame_energy = librosa.feature.rms(y=y, hop_length=hop_length)[0]
    threshold    = np.mean(frame_energy) * 1.3
    times        = librosa.frames_to_time(range(len(frame_energy)), sr=sr, hop_length=hop_length)

    segments = []
    start    = None
    for i, e in enumerate(frame_energy):
        if e > threshold and start is None:
            start = times[i]
        elif e <= threshold and start is not None:
            duration = times[i] - start
            if duration >= MIN_CLIP_DURATION:
                segments.append({
                    "start": start,
                    "end": min(start + MAX_CLIP_DURATION, times[i]),
                    "score_energy": float(np.mean(frame_energy[
                        int(start * sr / hop_length):int(times[i] * sr / hop_length)
                    ]))
                })
            start = None
    return segments

def _detect_pauses(y, sr) -> list:
    intervals = librosa.effects.split(y, top_db=25)
    segments  = []
    for start, end in intervals:
        t_start  = start / sr
        t_end    = end / sr
        duration = t_end - t_start
        if MIN_CLIP_DURATION <= duration <= MAX_CLIP_DURATION:
            segments.append({
                "start": t_start,
                "end": t_end,
                "score_pause": duration
            })
    return segments

def _detect_speech_density(y, sr) -> list:
    hop_length = 512
    zcr        = librosa.feature.zero_crossing_rate(y, hop_length=hop_length)[0]
    times      = librosa.frames_to_time(range(len(zcr)), sr=sr, hop_length=hop_length)
    threshold  = np.mean(zcr) * 1.1

    segments = []
    start    = None
    for i, z in enumerate(zcr):
        if z > threshold and start is None:
            start = times[i]
        elif z <= threshold and start is not None:
            duration = times[i] - start
            if duration >= MIN_CLIP_DURATION:
                segments.append({
                    "start": start,
                    "end": min(start + MAX_CLIP_DURATION, times[i]),
                    "score_density": float(np.mean(zcr))
                })
            start = None
    return segments

def _merge_segments(segments: list) -> list:
    if not segments:
        return []
    segments.sort(key=lambda x: x["start"])
    merged = []
    for seg in segments:
        if merged and seg["start"] < merged[-1]["end"] + 5:
            merged[-1]["end"]           = max(merged[-1]["end"], seg["end"])
            merged[-1]["score_energy"]  = max(merged[-1].get("score_energy", 0), seg.get("score_energy", 0))
            merged[-1]["score_pause"]   = max(merged[-1].get("score_pause", 0), seg.get("score_pause", 0))
            merged[-1]["score_density"] = max(merged[-1].get("score_density", 0), seg.get("score_density", 0))
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
            s.get("score_energy",  0) * 0.4 +
            s.get("score_pause",   0) * 0.3 +
            s.get("score_density", 0) * 0.3
        )
    segments.sort(key=score, reverse=True)
    return segments[:TARGET_CANDIDATES]

def _fallback_segments(duration: float, existing: list) -> list:
    existing_starts = {s["start"] for s in existing}
    segments = []
    start    = 0.0
    while start + MIN_CLIP_DURATION <= duration and len(segments) < TARGET_CANDIDATES:
        if start not in existing_starts:
            segments.append({
                "start": start,
                "end": min(start + MAX_CLIP_DURATION, duration),
                "score_energy": 0.1,
                "score_pause": 0.1,
                "score_density": 0.1
            })
        start += MIN_CLIP_DURATION
    return segments
