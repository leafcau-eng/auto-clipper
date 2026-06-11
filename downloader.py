import os
import yt_dlp
from config import DOWNLOAD_DIR, YOUTUBE_COOKIES

def download_video(url: str) -> str:
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    cookie_path = None
    if YOUTUBE_COOKIES:
        cookie_path = "cookies.txt"
        with open(cookie_path, "w") as f:
            f.write(YOUTUBE_COOKIES)

    ydl_opts = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "outtmpl": f"{DOWNLOAD_DIR}%(id)s.%(ext)s",
        "merge_output_format": "mp4",
        "quiet": False,
        "extractor_args": {
            "youtube": {
                "player_client": ["web"],
                "po_token": ["web+auto"],
            }
        },
    }

    if cookie_path:
        ydl_opts["cookiefile"] = cookie_path

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_id = info["id"]
            for ext in ["mp4", "mkv", "webm"]:
                path = f"{DOWNLOAD_DIR}{video_id}.{ext}"
                if os.path.exists(path):
                    print(f"[DOWNLOADER] Downloaded: {path}")
                    return path
    except Exception as e:
        raise Exception(f"Download failed: {e}")

def get_video_duration(video_path: str) -> float:
    import subprocess
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "format=duration", "-of", "default=noprint_wrappers=1:nokey=1",
         video_path],
        capture_output=True, text=True
    )
    return float(result.stdout.strip())
