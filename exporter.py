import os
import json
import subprocess
from datetime import datetime
from config import OUTPUT_DIR, CACHE_DIR
from subtitle import burn_subtitles
from cropper import crop_to_vertical


def generate_thumbnail(video_path: str, duration: float, thumb_path: str) -> str | None:
    """
    Generate thumbnail JPG dari frame di pertengahan video (50% durasi).
    Fallback minimal 0.5s kalau durasi sangat pendek.
    Return path thumbnail kalau sukses, None kalau gagal.
    Thumbnail adalah enhancement — kegagalan TIDAK menghentikan pipeline.
    """
    try:
        timestamp = max(duration * 0.5, 0.5)
        if timestamp >= duration:
            timestamp = max(duration / 2, 0.1)

        subprocess.run([
            "ffmpeg",
            "-ss", str(timestamp),
            "-i", video_path,
            "-frames:v", "1",
            "-q:v", "2",
            "-y",
            thumb_path
        ], check=True, capture_output=True)

        if os.path.exists(thumb_path):
            return thumb_path

        print(f"[EXPORTER] Thumbnail not created (unknown reason): {thumb_path}")
        return None

    except Exception as e:
        print(f"[EXPORTER] Thumbnail generation failed (non-fatal): {e}")
        return None


def export_clips(video_path: str, top_candidates: list) -> list:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    exported = []

    for i, candidate in enumerate(top_candidates):
        start    = candidate["start"]
        end      = candidate["end"]
        duration = end - start
        score    = candidate["score"]

        raw_file      = f"{OUTPUT_DIR}clip_{i+1}_raw.mp4"
        cropped_file  = f"{OUTPUT_DIR}clip_{i+1}_cropped.mp4"
        final_file    = f"{OUTPUT_DIR}clip_{i+1}_score{score}_{timestamp}.mp4"

        print(f"\n[EXPORTER] Clip {i+1}/{len(top_candidates)} | Score: {score} | Duration: {duration:.1f}s")

        # STEP 1 - Potong video
        print(f"[EXPORTER] Cutting clip...")
        subprocess.run([
            "ffmpeg",
            "-i", video_path,
            "-ss", str(start),
            "-t", str(duration),
            "-c:v", "libx264",
            "-c:a", "aac",
            "-y",
            raw_file
        ], check=True)

        # STEP 2 - Crop ke 9:16 + face detection
        print(f"[EXPORTER] Cropping to vertical 9:16...")
        crop_to_vertical(raw_file, cropped_file)

        # STEP 3 - Burn subtitle
        print(f"[EXPORTER] Burning subtitles...")
        final_path = burn_subtitles(cropped_file, candidate, final_file)

        # Cleanup temp files
        for f in [raw_file, cropped_file]:
            if os.path.exists(f) and f != final_path:
                os.remove(f)

        # STEP 4 - Generate thumbnail (non-fatal kalau gagal)
        print(f"[EXPORTER] Generating thumbnail...")
        thumb_file = final_path.rsplit(".", 1)[0] + "_thumb.jpg"
        thumbnail_file = generate_thumbnail(final_path, duration, thumb_file)

        meta = {
            "rank"             : i + 1,
            "score"            : score,
            "start"            : start,
            "end"              : end,
            "duration"         : duration,
            "reason"           : candidate.get("reason", ""),
            "hook"             : candidate.get("hook", ""),
            "emotional_trigger": candidate.get("emotional_trigger", ""),
            "transcript"       : candidate.get("transcript", ""),
            "file"             : final_path,
            "thumbnail_file"   : thumbnail_file
        }

        meta_file = final_path.replace(".mp4", ".json")
        with open(meta_file, "w") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        exported.append(meta)
        print(f"[EXPORTER] Saved: {final_path}")

    summary_file = f"{OUTPUT_DIR}summary_{timestamp}.json"
    with open(summary_file, "w") as f:
        json.dump(exported, f, ensure_ascii=False, indent=2)

    print(f"\n[EXPORTER] Done! {len(exported)} clips exported")
    return exported
