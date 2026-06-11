import os
import yt_dlp
from config import DOWNLOAD_DIR, YOUTUBE_COOKIES

def download_video(url: str) -> str:
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    # Tulis cookies ke file
    cookie_path = None
    if YOUTUBE_COOKIES:
        cookie_path = "cookies.txt"
        with open(cookie_path, "w") as f:
            f.write(YOUTUBE_COOKIES)

    # Coba format terbaik dulu, fallback ke format apapun
    formats = [
        "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]",
        "bestvideo+bestaudio/best",
        "best",
        "worst"
    ]

    for fmt in formats:
        try:
            ydl_opts = {
                "format": fmt,
                "outtmpl": f"{DOWNLOAD_DIR}%(id)s.%(ext)s",
                "quiet": False,
                "no_warnings": False,
                "merge_output_format": "mp4",
            }
            if cookie_path:
                ydl_opts["cookiefile"] = cookie_path

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                video_id = info["id"]
                # Cari file yang berhasil didownload
                for ext in ["mp4", "mkv", "webm", "avi"]:
                    path = f"{DOWNLOAD_DIR}{video_id}.{ext}"
                    if os.path.exists(path):
                        print(f"[DOWNLOADER] Downloaded: {path}")
                        return path

        except Exception as e:
            print(f"[DOWNLOADER] Format {fmt} failed: {e}, trying next...")
            continue

    raise Exception("All download formats failed!")

def get_video_duration(video_path: str) -> float:
    import subprocess
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "format=duration", "-of", "default=noprint_wrappers=1:nokey=1",
         video_path],
        capture_output=True, text=True
    )
    return float(result.stdout.strip())
