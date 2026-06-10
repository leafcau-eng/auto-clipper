import sys
import os
import requests
from downloader import download_video, get_video_duration
from candidate_finder import find_candidates
from transcriber import transcribe_candidates
from viral_ranker import rank_candidates
from exporter import export_clips

WEBHOOK_URL = "https://sch-web-cliper.vercel.app/api/webhook"
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

def send_webhook(project_id, status, clips=None, current_step=None, error_message=None):
    if not project_id:
        return
    try:
        payload = {
            "project_id": project_id,
            "status": status,
        }
        if current_step:
            payload["current_step"] = current_step
        if clips:
            payload["clips"] = clips
        if error_message:
            payload["error_message"] = error_message

        requests.post(
            WEBHOOK_URL,
            json=payload,
            headers={
                "x-webhook-secret": WEBHOOK_SECRET or "",
                "Content-Type": "application/json"
            },
            timeout=10
        )
        print(f"[WEBHOOK] Sent: {status}")
    except Exception as e:
        print(f"[WEBHOOK] Failed: {e}")

def run(url: str, project_id: str = None):
    print("=" * 50)
    print("   AUTO-CLIPPER V2")
    print("=" * 50)

    try:
        # STEP 1 - Download
        send_webhook(project_id, "processing", current_step="downloading")
        print("\n[STEP 1] Downloading video...")
        video_path = download_video(url)
        duration = get_video_duration(video_path)
        print(f"[STEP 1] Duration: {duration:.1f}s")

        # STEP 2 - Candidate Finder
        send_webhook(project_id, "processing", current_step="finding_candidates")
        print("\n[STEP 2] Finding candidates...")
        candidates = find_candidates(video_path)
        if not candidates:
            raise Exception("No candidates found!")

        # STEP 3 - Transcribe
        send_webhook(project_id, "processing", current_step="transcribing")
        print("\n[STEP 3] Transcribing candidates...")
        candidates = transcribe_candidates(video_path, candidates)

        # STEP 4 - Viral Ranker
        send_webhook(project_id, "processing", current_step="ranking")
        print("\n[STEP 4] Ranking candidates...")
        top_clips = rank_candidates(candidates)

        # STEP 5 - Export
        send_webhook(project_id, "processing", current_step="exporting")
        print("\n[STEP 5] Exporting top clips...")
        exported = export_clips(video_path, top_clips)

        # Format clips buat webhook
        clips_data = [{
            "title": f"Clip {c['rank']}",
            "duration": c["end"] - c["start"],
            "start": c["start"],
            "end": c["end"],
            "file_url": None,
            "thumbnail_url": None,
        } for c in exported]

        send_webhook(project_id, "completed", clips=clips_data)

        print("\n" + "=" * 50)
        print(f"   DONE! {len(exported)} clips exported")
        print("=" * 50)

    except Exception as e:
        print(f"\n[ERROR] {e}")
        send_webhook(project_id, "failed", error_message=str(e))
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py <url> [project_id]")
        sys.exit(1)

    url = sys.argv[1]
    project_id = sys.argv[2] if len(sys.argv) > 2 else None
    run(url, project_id)
