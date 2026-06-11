import os
import subprocess

EMOTION_COLORS = {
    "semangat":   "&H0000FFFF",
    "inspiratif": "&H0000FFFF",
    "terkejut":   "&H000000FF",
    "sedih":      "&H00FF6B6B",
    "lucu":       "&H0000FF00",
    "marah":      "&H000000FF",
    "default":    "&H00FFFFFF",
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
    segments  = candidate.get("whisper_segments", [])
    emotional = candidate.get("emotional_trigger", "")
    clip_start = candidate.get("start", 0)

    if not segments:
        print("[SUBTITLE] No segments, skipping")
        return video_path

    print("[SUBTITLE] Generating dynamic word subtitles...")
    color     = get_emotion_color(emotional)
    ass_path  = output_path.replace(".mp4", ".ass")
    final_path = output_path.replace(".mp4", "_sub.mp4")

    _create_ass_dynamic(segments, ass_path, color, clip_start)

    subprocess.run([
        "ffmpeg", "-i", video_path,
        "-vf", f"ass={ass_path}",
        "-c:a", "aac", "-y",
        final_path
    ], check=True)

    print(f"[SUBTITLE] Done: {final_path}")
    return final_path

def _create_ass_dynamic(segments, ass_path, color, clip_start=0):
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Word,Arial Black,95,{color},&H000000FF,&H00000000,&H90000000,-1,0,0,0,100,100,3,0,1,6,3,5,60,60,960,1
Style: Highlight,Arial Black,105,&H0000FFFF,&H000000FF,&H00000000,&H90000000,-1,0,0,0,100,100,3,0,1,6,3,5,60,60,960,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = ""

    for seg in segments:
        words = seg.get("words", [])
        if not words:
            # Fallback segment level
            start = max(0, seg["start"] - clip_start)
            end   = max(0, seg["end"] - clip_start)
            text  = seg["text"].strip().upper()
            events += f"Dialogue: 0,{_t(start)},{_t(end)},Word,,0,0,0,,{{\\b1\\an5}}{text}\n"
            continue

        # Group 3 kata per baris
        chunks = [words[i:i+3] for i in range(0, len(words), 3)]

        for chunk in chunks:
            if not chunk:
                continue

            for j, word in enumerate(chunk):
                w_start = max(0, word["start"] - clip_start)
                w_end   = max(0, word["end"]   - clip_start)

                # Build line - kata aktif pakai Highlight style + lebih besar
                line = ""
                for k, w in enumerate(chunk):
                    txt = w["word"].strip().upper()
                    if k == j:
                        # Kata aktif - kuning, lebih besar, bold
                        line += f"{{\\c&H0000FFFF&\\fs110\\b1\\t(0,80,\\fscx120\\fscy120)\\t(80,160,\\fscx100\\fscy100)}}{txt}  "
                    else:
                        # Kata lain - warna normal, lebih kecil
                        line += f"{{\\c{color}&\\fs85\\b1}}{txt}  "

                events += f"Dialogue: 0,{_t(w_start)},{_t(w_end)},Word,,0,0,0,,{{\\an5}}{line.strip()}\n"

    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(header + events)

def _t(seconds):
    h  = int(seconds // 3600)
    m  = int((seconds % 3600) // 60)
    s  = int(seconds % 60)
    cs = int((seconds % 1) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"
