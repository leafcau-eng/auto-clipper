import os
import yt_dlp
from config import DOWNLOAD_DIR, YOUTUBE_COOKIES

INVIDIOUS_INSTANCES = [
    "https://invidious.snopyta.org",
    "https://yewtu.be",
    "https://invidious.kavin.rocks",
    "https://vid.puffyan.us",
]

def convert_to_invidious(url: str) -> list:
    """Convert YouTube URL ke beberapa Invidious instance"""
    video_id = None
    
    if "youtu.be/" in url:
        video_id = url.split("youtu.be/")[1].split("?")[0]
    elif "youtube.com/watch" in url:
        video_id = url.split("v=")[1].split("&")[0]
    elif "youtube.com/shorts" in url:
        video_id = url.split("shorts/")[1].split("?")[0]
    
    if not video_id:
        return [url]
    
    urls = []
    for instance in INVIDIOUS_INSTANCES:
        urls.append(f"{instance}/watch?v={video_id}")
    urls.append(url)  # fallback ke URL asli
    return urls

def download_video(url: str) -> str:
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    cookie_path = None
    if YOUTUBE_COOKIES:
        cookie_path = "cookies.txt"
        with open(cookie_path, "w") as f:
            f.write(YOUTUBE_COOKIES)

    urls_to_try = convert_to_invidious(url)
    
    for try_url in urls_to_try:
        print(f"[DOWNLOADER] Trying: {try_url}")
        try:
            ydl_opts = {
                "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
                "outtmpl": f"{DOWNLOAD_DIR}%(id)s.%(ext)s",
                "merge_output_format": "mp4",
                "quiet": False,
            }
            if cookie_path:
                ydl_opts["cookiefile"] = cookie_path

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(try_url, download=True)
                video_id = info["id"]
                for ext in ["mp4", "mkv", "webm"]:
                    path = f"{DOWNLOAD_DIR}{video_id}.{ext}"
                    if os.path.exists(path):
                        print(f"[DOWNLOADER] Downloaded: {path}")
                        return path
        except Exception as e:
            print(f"[DOWNLOADER] Failed {try_url}: {e}, trying next...")
            continue

    raise Exception("All download attempts failed!")

def get_video_duration(video_path: str) -> float:
    import subprocess
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "format=duration", "-of", "default=noprint_wrappers=1:nokey=1",
         video_path],
        capture_output=True, text=True
    )
    return float(result.stdout.strip())
