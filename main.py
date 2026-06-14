import sys
import os
import requests
from downloader import download_video, get_video_duration
from candidate_finder import find_candidates
from transcriber import transcribe_candidates
from viral_ranker import rank_candidates
from exporter import export_clips

WEBHOOK_URL = "https://ai-creator-hub-zeta.vercel.app/api/webhook"
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")


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


def upload_clip_to_storage(file_path: str, project_id: str, clip_index: int) -> str | None:
    """
    Upload clip ke Supabase Storage bucket 'assets'.
    Return public URL kalau sukses, None kalau gagal.
    Path: clips/{project_id}/clip_{clip_index}.mp4
    """
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        print(f"[STORAGE] Skipped — SUPABASE_URL or SUPABASE_SERVICE_KEY not set")
        return None

    if not os.path.exists(file_path):
        print(f"[STORAGE] File not found: {file_path}")
        return None

    try:
        from supabase import create_client
        supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

        storage_path = f"clips/{project_id}/clip_{clip_index}.mp4"

        with open(file_path, "rb") as f:
            supabase.storage.from_("assets").upload(
                path=storage_path,
                file=f,
                file_options={"content-type": "video/mp4", "upsert": "true"}
            )

        # Ambil public URL
        result = supabase.storage.from_("assets").get_public_url(storage_path)
        public_url = result if isinstance(result, str) else result.get("publicUrl")

        print(f"[STORAGE] Uploaded clip_{clip_index}: {public_url}")
        return public_url

    except Exception as e:
        print(f"[STORAGE] Upload failed for clip_{clip_index}: {e}")
        return None


def upload_thumbnail_to_storage(file_path: str | None, project_id: str, clip_index: int) -> str | None:
    """
    Upload thumbnail JPG ke Supabase Storage bucket 'assets'.
    Return public URL kalau sukses, None kalau gagal/tidak ada file.
    Path: clips/{project_id}/clip_{clip_index}_thumb.jpg
    Non-fatal: kegagalan tidak menghentikan pipeline.
    """
    if not file_path or not os.path.exists(file_path):
        return None

    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        print(f"[STORAGE] Thumbnail skipped — SUPABASE_URL or SUPABASE_SERVICE_KEY not set")
        return None

    try:
        from supabase import create_client
        supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

        storage_path = f"clips/{project_id}/clip_{clip_index}_thumb.jpg"

        with open(file_path, "rb") as f:
            supabase.storage.from_("assets").upload(
                path=storage_path,
                file=f,
                file_options={"content-type": "image/jpeg", "upsert": "true"}
            )

        result = supabase.storage.from_("assets").get_public_url(storage_path)
        public_url = result if isinstance(result, str) else result.get("publicUrl")

        print(f"[STORAGE] Uploaded thumbnail clip_{clip_index}: {public_url}")
        return public_url

    except Exception as e:
        print(f"[STORAGE] Thumbnail upload failed for clip_{clip_index} (non-fatal): {e}")
        return None


def run(url: str, project_id: str):
    if not project_id:
        print("ERROR: project_id is required")
        sys.exit(1)
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

        # STEP 6 - Upload ke Supabase Storage
        send_webhook(project_id, "processing", current_step="uploading")
        print("\n[STEP 6] Uploading clips to storage...")

        clips_data = []
        for i, c in enumerate(exported):
            file_url = None
            thumbnail_url = None

            if project_id:
                file_url = upload_clip_to_storage(
                    file_path=c["file"],
                    project_id=project_id,
                    clip_index=i + 1
                )
                thumbnail_url = upload_thumbnail_to_storage(
                    file_path=c.get("thumbnail_file"),
                    project_id=project_id,
                    clip_index=i + 1
                )

            clips_data.append({
                "title": f"Clip {c['rank']}",
                "duration": c["end"] - c["start"],
                "start": c["start"],
                "end": c["end"],
                "file_url": file_url,
                "thumbnail_url": thumbnail_url,
                "score": c.get("score"),
                "hook": c.get("hook", ""),
                "reason": c.get("reason", ""),
            })

        send_webhook(project_id, "done", clips=clips_data)

        print("\n" + "=" * 50)
        print(f"   DONE! {len(exported)} clips exported")
        uploaded = sum(1 for c in clips_data if c["file_url"])
        print(f"   {uploaded}/{len(exported)} clips uploaded to storage")
        print("=" * 50)

    except Exception as e:
        print(f"\n[ERROR] {e}")
        send_webhook(project_id, "failed", error_message=str(e))
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python main.py <url> <project_id>")
        print("ERROR: project_id is required")
        sys.exit(1)

    url = sys.argv[1]
    project_id = sys.argv[2]
    run(url, project_id)


