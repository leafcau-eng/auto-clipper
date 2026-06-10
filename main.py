import sys
from downloader import download_video, get_video_duration
from candidate_finder import find_candidates
from transcriber import transcribe_candidates
from viral_ranker import rank_candidates
from exporter import export_clips

def run(url: str):
    print("=" * 50)
    print("   AUTO-CLIPPER V2")
    print("=" * 50)

    # STEP 1 - Download
    print("\n[STEP 1] Downloading video...")
    video_path = download_video(url)
    duration   = get_video_duration(video_path)
    print(f"[STEP 1] Duration: {duration:.1f}s")

    # STEP 2 - Candidate Finder
    print("\n[STEP 2] Finding candidates...")
    candidates = find_candidates(video_path)
    if not candidates:
        print("[ERROR] No candidates found!")
        return

    # STEP 3 - Transcribe
    print("\n[STEP 3] Transcribing candidates...")
    candidates = transcribe_candidates(video_path, candidates)

    # STEP 4 - Viral Ranker
    print("\n[STEP 4] Ranking candidates...")
    top_clips = rank_candidates(candidates)

    # STEP 5 - Export
    print("\n[STEP 5] Exporting top clips...")
    exported = export_clips(video_path, top_clips)

    print("\n" + "=" * 50)
    print(f"   DONE! {len(exported)} clips exported")
    print("=" * 50)
    for clip in exported:
        print(f"  #{clip['rank']} Score: {clip['score']} | {clip['file']}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py <youtube_url>")
        sys.exit(1)
    run(sys.argv[1])
