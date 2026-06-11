import os
import json
import subprocess
from config import OUTPUT_DIR, CACHE_DIR

# Warna berdasarkan emosi
EMOTION_COLORS = {
    "semangat":    "&H0000FFFF",  # Kuning
    "inspiratif":  "&H0000FFFF",  # Kuning
    "terkejut":    "&H000000FF",  # Merah
    "sedih":       "&H00FF6B6B",  # Biru muda
    "lucu":        "&H0000FF00",  # Hijau
    "marah":       "&H000000FF",  # Merah
    "default":     "&H00FFFFFF",  # Putih
}

def get_emotion_color(emotional_trigger: str) -> str:
    if not emotional_trigger:
        return EMOTION_COLORS["default"]
    trigger = emotional_trigger.lower()
    for key in EMOTION_COLORS:
        if key in trigger:
            return EMOTION_COLORS[key]
    return EMOTION_COLORS["default"]

def burn_subtitles(video_path: str, candidate: dict, output_path: str) -> str:
    transcript = candidate.get("transcript", "")
    emotional_trigger = candidate.get("emotional_trigger", "")
    start = candidate.get("start", 0)

    if not transcript:
        print(f"[SUBTITLE] No transcript, skipping subtitles")
        return video_path

    print(f"[SUBTITLE] Generating subtitles...")
    color = get_emotion_color(emotional_trigger)
    highlight_color = "&H0000FFFF"  # Kuning untuk highlight aktif

    # Buat SRT dari transcript whisper segments
    srt_path = output_path.replace(".mp4", ".srt")
    ass_path = output_path.replace(".mp4", ".ass")

    # Pakai whisper segments kalau ada
    segments = candidate.get("whisper_segments", [])
    if segments:
        _create_srt_from_segments(segments, srt_path, start)
    else:
        _create_srt_simple(transcript, srt_path, start, candidate["end"] - start)

    # Convert SRT ke ASS dengan style Hormozi
    _create_ass_style(srt_path, ass_path, color, highlight_color)

    # Burn ke video
    final_path = output_path.replace(".mp4", "_sub.mp4")
    subprocess.run([
        "ffmpeg",
        "-i", video_path,
        "-vf", f"ass={ass_path}",
        "-c:a", "aac",
        "-y",
        final_path
    ], check=True)

    print(f"[SUBTITLE] Done: {final_path}")
    return final_path

def _create_srt_from_segments(segments, srt_path, offset=0):
    with open(srt_path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(segments):
            start = max(0, seg["start"] - offset)
            end   = max(0, seg["end"] - offset)
            text  = seg["text"].strip()
            f.write(f"{i+1}\n")
            f.write(f"{_format_time(start)} --> {_format_time(end)}\n")
            f.write(f"{text}\n\n")

def _create_srt_simple(transcript, srt_path, offset, duration):
    words = transcript.split()
    if not words:
        return

    time_per_word = duration / len(words)
    chunks = [words[i:i+5] for i in range(0, len(words), 5)]

    with open(srt_path, "w", encoding="utf-8") as f:
        for i, chunk in enumerate(chunks):
            start = i * 5 * time_per_word
            end   = min(start + 5 * time_per_word, duration)
            text  = " ".join(chunk)
            f.write(f"{i+1}\n")
            f.write(f"{_format_time(start)} --> {_format_time(end)}\n")
            f.write(f"{text}\n\n")

def _create_ass_style(srt_path, ass_path, color, highlight_color):
    # Header ASS dengan style Hormozi
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial Black,90,{color},&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,2,2,80,80,200,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    with open(srt_path, "r", encoding="utf-8") as f:
        content = f.read()

    events = ""
    blocks = content.strip().split("\n\n")
    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) < 3:
            continue
        times = lines[1].split(" --> ")
        if len(times) != 2:
            continue
        start = _srt_to_ass_time(times[0].strip())
        end   = _srt_to_ass_time(times[1].strip())
        text  = " ".join(lines[2:]).upper()
        # Bold + outline effect
        text  = f"{{\\b1\\an2}}{text}"
        events += f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}\n"

    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(header + events)

def _format_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def _srt_to_ass_time(srt_time):
    srt_time = srt_time.replace(",", ".")
    parts = srt_time.split(":")
    h, m = parts[0], parts[1]
    s = parts[2]
    return f"{h}:{m}:{s}"
