import os
import json
import subprocess
from datetime import datetime
from config import OUTPUT_DIR, CACHE_DIR

def export_clips(video_path: str, top_candidates: list) -> list:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    exported = []

    for i, candidate in enumerate(top_candidates):
        start    = candidate["start"]
        end      = candidate["end"]
        duration = end - start
        score    = candidate["score"]

        output_file = f"{OUTPUT_DIR}clip_{i+1}_score{score}_{timestamp}.mp4"

        print(f"[EXPORTER] Exporting clip {i+1}/{len(top_candidates)} | Score: {score} | Duration: {duration:.1f}s")

        subprocess.run([
            "ffmpeg",
            "-i", video_path,
            "-ss", str(start),
            "-t", str(duration),
            "-c:v", "libx264",
            "-c:a", "aac",
            "-y",
            output_file
        ], check=True)

        # Simpan metadata
        meta = {
            "rank"      : i + 1,
            "score"     : score,
            "start"     : start,
            "end"       : end,
            "duration"  : duration,
            "reason"    : candidate.get("reason", ""),
            "hook"      : candidate.get("hook", ""),
            "transcript": candidate.get("transcript", ""),
            "file"      : output_file
        }
        meta_file = output_file.replace(".mp4", ".json")
        with open(meta_file, "w") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        exported.append(meta)
        print(f"[EXPORTER] Saved: {output_file}")

    # Summary
    summary_file = f"{OUTPUT_DIR}summary_{timestamp}.json"
    with open(summary_file, "w") as f:
        json.dump(exported, f, ensure_ascii=False, indent=2)

    print(f"\n[EXPORTER] Done! {len(exported)} clips exported")
    print(f"[EXPORTER] Summary: {summary_file}")
    return exported
