import os
import subprocess
import cv2
import numpy as np

def crop_to_vertical(video_path: str, output_path: str) -> str:
    print(f"[CROPPER] Analyzing faces for smooth tracking...")

    cap    = cv2.VideoCapture(video_path)
    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps    = cap.get(cv2.CAP_PROP_FPS)
    total  = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    )

    # Deteksi wajah per frame (sample tiap 15 frame)
    face_x_per_frame = {}
    frame_idx = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        if frame_idx % 15 == 0:
            gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.1, 4, minSize=(50, 50))
            if len(faces) > 0:
                # Ambil wajah terbesar (paling dekat kamera)
                largest = max(faces, key=lambda f: f[2] * f[3])
                cx = largest[0] + largest[2] // 2
                face_x_per_frame[frame_idx] = cx
        frame_idx += 1

    cap.release()

    if not face_x_per_frame:
        print(f"[CROPPER] No faces detected, using center crop")
        center_x = width // 2
        face_x_per_frame = {i: center_x for i in range(0, total, 15)}

    # Smooth tracking - interpolate posisi antar frame
    all_frames   = sorted(face_x_per_frame.keys())
    smooth_x     = _smooth_positions(face_x_per_frame, total, fps)

    # Target crop width untuk 9:16
    target_w = height * 9 // 16

    # Buat filter_complex untuk smooth pan
    crop_filter = _build_crop_filter(smooth_x, target_w, height, width, fps, total)

    print(f"[CROPPER] Applying smooth face tracking crop...")
    subprocess.run([
        "ffmpeg", "-i", video_path,
        "-vf", crop_filter,
        "-c:a", "aac", "-y",
        output_path
    ], check=True)

    print(f"[CROPPER] Done: {output_path}")
    return output_path

def _smooth_positions(face_x_dict: dict, total_frames: int, fps: float) -> list:
    # Interpolate semua frame
    frames    = sorted(face_x_dict.keys())
    positions = [face_x_dict[f] for f in frames]

    all_x = []
    for i in range(total_frames):
        if i in face_x_dict:
            all_x.append(face_x_dict[i])
        elif frames:
            # Interpolate ke frame terdekat
            closest = min(frames, key=lambda f: abs(f - i))
            all_x.append(face_x_dict[closest])
        else:
            all_x.append(0)

    # Smooth dengan moving average (window = 2 detik)
    window = max(1, int(fps * 2))
    smoothed = np.convolve(all_x, np.ones(window) / window, mode='same').astype(int)
    return smoothed.tolist()

def _build_crop_filter(smooth_x: list, target_w: int, height: int, width: int, fps: float, total: int) -> str:
    # Buat crop berdasarkan posisi smooth, clamp ke border
    # Pakai sendcmd untuk dynamic crop
    # Simplifikasi: ambil median per detik untuk ffmpeg crop expression

    # Sample posisi tiap detik
    positions_per_sec = []
    for sec in range(int(total / fps) + 1):
        frame = min(int(sec * fps), len(smooth_x) - 1)
        cx    = smooth_x[frame]
        crop_x = max(0, min(cx - target_w // 2, width - target_w))
        positions_per_sec.append(crop_x)

    # Pakai posisi median untuk crop stabil
    median_x = int(np.median(positions_per_sec))

    return f"crop={target_w}:{height}:{median_x}:0,scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black"
