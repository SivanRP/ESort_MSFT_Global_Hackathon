"""
E-Waste Classifier — Groq Vision + Webcam with GUI
Uses Groq's free Llama 4 Scout vision model for classification.
Shows a live camera window with classification labels.
"""

import base64
import io
import os
import time
import threading
import requests
from PIL import Image, ImageTk
import tkinter as tk
import av

# -----------------------------
# Configuration
# -----------------------------
GROQ_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

CLASSIFY_PROMPT = """Look at this image carefully. Your job is to classify e-waste items for a sorting machine.

If there is NO e-waste item visible (just a person, desk, wall, room, etc.), respond with exactly: NOTHING

If you see an e-waste item, respond with ONLY ONE of these exact words:
- BATTERY (batteries of any kind)
- PCB (printed circuit boards, motherboards, green/brown boards with electronic components soldered on)
- KEYBOARD (computer keyboards)
- MOUSE (computer mice)
- MOBILE (phones, smartphones, tablets)
- CHARGER (chargers, power adapters, power bricks, AC adapters)
- CABLE (loose cables, wires, cords)
- METAL (large metal appliances: microwaves, washing machines, metal PC cases)

Respond with ONLY the single category word. Nothing else."""

CLASS_MAP = {
    "BATTERY": "Battery",
    "PCB": "PCB",
    "KEYBOARD": "Plastic",
    "MOUSE": "Plastic",
    "MOBILE": "Plastic",
    "CHARGER": "Plastic",
    "CABLE": "Misc",
    "METAL": "Metal",
    "NOTHING": "Nothing",
}

CATEGORY_COLORS = {
    "Battery": "#FF4444",
    "PCB": "#44FF44",
    "Plastic": "#4488FF",
    "Metal": "#FFAA00",
    "Misc": "#AAAAAA",
    "Nothing": "#555555",
}


def classify_frame(frame_bytes: bytes) -> tuple:
    """Classify image bytes using Groq vision API."""
    img_b64 = base64.b64encode(frame_bytes).decode("utf-8")
    try:
        r = requests.post(GROQ_URL,
            headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
            json={
                "model": MODEL,
                "messages": [{"role": "user", "content": [
                    {"type": "text", "text": CLASSIFY_PROMPT},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
                ]}],
                "max_tokens": 10,
                "temperature": 0.1,
            }, timeout=10)

        if r.status_code != 200:
            print(f"Groq error: {r.status_code}")
            return "NOTHING", "Nothing"

        answer = r.json()["choices"][0]["message"]["content"].strip().upper()
        for key in CLASS_MAP:
            if key in answer:
                return key, CLASS_MAP[key]
        return "NOTHING", "Nothing"
    except Exception as e:
        print(f"Error: {e}")
        return "NOTHING", "Nothing"


# -----------------------------
# GUI
# -----------------------------
root = tk.Tk()
root.title("E-Waste Classifier")
root.configure(bg="#1a1a2e")

tk.Label(root, text="E-WASTE CLASSIFIER", font=("Segoe UI", 24, "bold"),
         fg="#00d4aa", bg="#1a1a2e").pack(pady=(15, 5))
tk.Label(root, text="Groq AI Vision — Free & Fast",
         font=("Segoe UI", 12), fg="#888888", bg="#1a1a2e").pack(pady=(0, 10))

cam_label = tk.Label(root, bg="#000000", width=640, height=480)
cam_label.pack(padx=20, pady=5)

status_label = tk.Label(root, text="● WARMING UP", font=("Segoe UI", 10),
                        fg="#FFAA00", bg="#1a1a2e")
status_label.pack(pady=(5, 0))

result_frame = tk.Frame(root, bg="#16213e", padx=20, pady=15)
result_frame.pack(fill="x", padx=20, pady=10)

result_label = tk.Label(result_frame, text="Starting camera...",
                        font=("Segoe UI", 22, "bold"), fg="#FFFFFF", bg="#16213e")
result_label.pack()

detail_label = tk.Label(result_frame, text="Classifications update every 2 seconds",
                        font=("Segoe UI", 13), fg="#AAAAAA", bg="#16213e")
detail_label.pack()

photo_ref = [None]
running = [True]
current_result = [None]


def classify_thread(img_bytes):
    """Run classification in separate thread."""
    detected, category = classify_frame(img_bytes)
    current_result[0] = (detected, category)


def cam_loop():
    """Camera capture loop."""
    container = av.open("video=Surface Camera Front", format="dshow")
    stream = container.streams.video[0]
    frame_count = 0
    last_classify = 0
    classifying = False

    for packet in container.demux(stream):
        if not running[0]:
            break
        for frame in packet.decode():
            if not running[0]:
                break
            frame_count += 1
            if frame_count < 10:
                continue

            # Update camera display
            img = frame.to_image()
            img_display = img.resize((640, 480), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img_display)
            photo_ref[0] = photo
            cam_label.config(image=photo)

            # Classify every 2 seconds
            now = time.time()
            if now - last_classify >= 2.0 and not classifying:
                last_classify = now
                classifying = True
                status_label.config(text="● ANALYZING...", fg="#FFAA00")

                img_small = img.resize((512, 512), Image.LANCZOS)
                buf = io.BytesIO()
                img_small.save(buf, format="JPEG", quality=75)

                t = threading.Thread(target=classify_thread, args=(buf.getvalue(),), daemon=True)
                t.start()

            # Check if classification finished
            if classifying and current_result[0] is not None:
                detected, category = current_result[0]
                current_result[0] = None
                classifying = False

                color = CATEGORY_COLORS.get(category, "#FFFFFF")
                status_label.config(text="● READY", fg="#44FF44")

                if category == "Nothing":
                    result_label.config(text="NO E-WASTE DETECTED", fg="#555555")
                    detail_label.config(text="Point camera at an e-waste item")
                else:
                    result_label.config(text=f"Sort: {category.upper()}", fg=color)
                    detail_label.config(text=f"Detected: {detected}")

            time.sleep(0.03)

    container.close()


def on_close():
    running[0] = False
    root.destroy()


root.protocol("WM_DELETE_WINDOW", on_close)
cam_thread = threading.Thread(target=cam_loop, daemon=True)
cam_thread.start()

print("=" * 50)
print("  E-WASTE CLASSIFIER")
print("=" * 50)
print("Using: Groq Llama 4 Scout Vision (free)")
print("Close the window to quit.")
print("=" * 50)

root.mainloop()

