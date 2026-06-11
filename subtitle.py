import os
import subprocess
import cv2
import numpy as np

def get_subtitle_position(video_path: str) -> int:
    """Detect area kosong di video, return margin bottom dalam pixel"""
    cap = cv2.VideoCapture(video_path)
    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Sample 10 frame
    samples = []
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    step  = max(1, total // 10)

    for i in range(0, min(total, 10 * step), step):
        cap.set(cv2.CAP_PROP_POS_FRAMES, i)
        ret, frame = cap.read()
        if ret:
            samples.append(frame)
    cap.release()

    if not samples:
        return height // 3  # default bawah

    avg_frame = np.mean(samples, axis=0).astype(np.uint8)
    gray = cv2.cvtColor(avg_frame, cv2.COLOR_BGR2GRAY)

    # Deteksi brightness per baris horizontal
    row_brightness = np.mean(gray, axis=1)

    # Cari area paling gelap (kosong/background) di sepertiga bawah
    bottom_third = row_brightness[height * 2 // 3:]
    darkest_row = np.argmin(bottom_third) + height * 2 // 3

    # Convert ke margin dari bawah
    margin = height - darkest_row
    margin = max(150, min(margin, height // 2))

    print(f"[SUBTITLE] Auto position: margin_bottom={margin}px")
    return margin

def burn_subtitles(video_path: str, candidate: dict, output_path: str) -> str:
    segments   = candidate.get("whisper_segments", [])
    clip_start = candidate.get("start", 0)

    if not segments:
        print("[SUBTITLE] No segments, skipping")
        return video_path

    print("[SUBTITLE] Detecting subtitle position...")
    margin_v = get_subtitle_position(video_path)

    print("[SUBTITLE] Generating dynamic word subtitles...")
    ass_path   = output_path.replace(".mp4", ".ass")
    final_path = output_path.replace(".mp4", "_sub.mp4")

    _create_ass(segments, ass_path, clip_start, margin_v)

    subprocess.run([
        "ffmpeg", "-i", video_path,
        "-vf", f"ass={ass_path}",
        "-c:a", "aac", "-y",
        final_path
    ], check=True)

    print(f"[SUBTITLE] Done: {final_path}")
    return final_path

def _create_ass(segments, ass_path, clip_start=0, margin_v=300):
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Normal,Arial Black,90,&H00FFFFFF,&H000000FF,&H00000000,&HAA000000,-1,0,0,0,100,100,2,0,1,5,2,2,80,80,{margin_v},1
Style: Active,Arial Black,100,&H0000FFFF,&H000000FF,&H00000000,&HAA000000,-1,0,0,0,100,100,2,0,1,5,2,2,80,80,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = ""

    for seg in segments:
        words = seg.get("words", [])

        if not words:
            start = max(0, seg["start"] - clip_start)
            end   = max(0, seg["end"]   - clip_start)
            text  = seg["text"].strip().upper()
            events += f"Dialogue: 0,{_t(start)},{_t(end)},Normal,,0,0,0,,{{\\b1\\an2}}{text}\n"
            continue

        # Group 3 kata per baris
        chunks = [words[i:i+3] for i in range(0, len(words), 3)]

        for chunk in chunks:
            if not chunk:
                continue
            for j, word in enumerate(chunk):
                w_start = max(0, word["start"] - clip_start)
                w_end   = max(0, word["end"]   - clip_start)

                # Build line
                line = ""
                for k, w in enumerate(chunk):
                    txt = w["word"].strip().upper()
                    if k == j:
                        # Kata aktif - KUNING + lebih besar
                        line += f"{{\\c&H0000FFFF&\\fs105\\b1}}{txt}{{\\r}} "
                    else:
                        # Kata lain - PUTIH
                        line += f"{{\\c&H00FFFFFF&\\fs90\\b1}}{txt}{{\\r}} "

                events += f"Dialogue: 0,{_t(w_start)},{_t(w_end)},Normal,,0,0,0,,{{\\an2}}{line.strip()}\n"

    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(header + events)

def _t(seconds):
    h  = int(seconds // 3600)
    m  = int((seconds % 3600) // 60)
    s  = int(seconds % 60)
    cs = int((seconds % 1) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"
