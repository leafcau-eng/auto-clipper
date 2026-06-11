import os
import subprocess
import cv2
import numpy as np

def crop_to_vertical(video_path: str, output_path: str) -> str:
    print(f"[CROPPER] Detecting faces and cropping to 9:16...")

    # Deteksi posisi wajah dominan
    cap = cv2.VideoCapture(video_path)
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps    = cap.get(cv2.CAP_PROP_FPS)
    total  = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # Sample tiap 30 frame buat deteksi wajah
    face_positions = []
    frame_count = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        if frame_count % 30 == 0:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.1, 4)
            for (x, y, w, h) in faces:
                cx = x + w // 2
                face_positions.append(cx)
        frame_count += 1

    cap.release()

    # Tentukan crop center X
    if face_positions:
        avg_x = int(np.median(face_positions))
        print(f"[CROPPER] Face detected at x={avg_x}")
    else:
        avg_x = width // 2
        print(f"[CROPPER] No face detected, using center x={avg_x}")

    # Hitung crop area 9:16
    target_w = height * 9 // 16
    crop_x = max(0, avg_x - target_w // 2)
    crop_x = min(crop_x, width - target_w)

    print(f"[CROPPER] Crop: x={crop_x}, w={target_w}, h={height}")

    # Crop + resize ke 1080x1920
    subprocess.run([
        "ffmpeg",
        "-i", video_path,
        "-vf", f"crop={target_w}:{height}:{crop_x}:0,scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
        "-c:a", "aac",
        "-y",
        output_path
    ], check=True)

    print(f"[CROPPER] Done: {output_path}")
    return output_path
