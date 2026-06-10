import os
import yt_dlp
from config import DOWNLOAD_DIR, YOUTUBE_COOKIES

def download_video(url: str) -> str:
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    ydl_opts = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]",
        "outtmpl": f"{DOWNLOAD_DIR}%(id)s.%(ext)s",
        "quiet": False,
        "no_warnings": False,
    }

    # Pakai cookies kalau ada
    if YOUTUBE_COOKIES:
        cookie_path = "cookies.txt"
        with open(cookie_path, "w") as f:
            f.write(YOUTUBE_COOKIES)
        ydl_opts["cookiefile"] = cookie_path

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        video_id = info["id"]
        ext = info["ext"]
        output_path = f"{DOWNLOAD_DIR}{video_id}.{ext}"
        print(f"[DOWNLOADER] Downloaded: {output_path}")
        return output_path

def get_video_duration(video_path: str) -> float:
    import subprocess
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "format=duration", "-of", "default=noprint_wrappers=1:nokey=1",
         video_path],
        capture_output=True, text=True
    )
    return float(result.stdout.strip())
