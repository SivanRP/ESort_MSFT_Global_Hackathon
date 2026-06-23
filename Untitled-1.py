"""
E-Waste Classifier — Groq Vision + Webcam with GUI + Arduino Servo
Uses Groq's free Llama 4 Scout vision model for classification.
Sends sort commands to Arduino via serial to move servo into bins.
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

# Try to import serial for Arduino communication
try:
    import serial
    import serial.tools.list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False

# -----------------------------
# Configuration
# -----------------------------
GROQ_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
ARDUINO_BAUD = 9600

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
# Arduino Serial Connection
# -----------------------------
def find_arduino():
    """Auto-detect Arduino serial port."""
    if not SERIAL_AVAILABLE:
        print("[WARN] pyserial not installed. Run: pip install pyserial")
        return None
    ports = serial.tools.list_ports.comports()
    for port in ports:
        # Arduino typically shows as CH340, Arduino, or USB Serial
        if any(kw in port.description.lower() for kw in ["arduino", "ch340", "usb serial", "usb-serial"]):
            return port.device
    # If no Arduino-specific port found, try first available COM port
    for port in ports:
        if "COM" in port.device or "ttyUSB" in port.device or "ttyACM" in port.device:
            return port.device
    return None


def connect_arduino():
    """Connect to Arduino. Returns serial connection or None."""
    port = find_arduino()
    if port is None:
        print("[INFO] No Arduino detected. Running in display-only mode.")
        return None
    try:
        ser = serial.Serial(port, ARDUINO_BAUD, timeout=2)
        time.sleep(2)  # Wait for Arduino reset
        # Read the READY message
        response = ser.readline().decode().strip()
        if "READY" in response:
            print(f"[INFO] Arduino connected on {port}")
        else:
            print(f"[INFO] Arduino on {port} (no READY signal, continuing anyway)")
        return ser
    except Exception as e:
        print(f"[WARN] Could not connect to Arduino on {port}: {e}")
        return None


def send_to_arduino(ser, category):
    """Send sort command to Arduino."""
    if ser is None:
        return
    # Map category to Arduino command
    cmd_map = {
        "Battery": "BATTERY",
        "PCB": "PCB",
        "Plastic": "PLASTIC",
        "Metal": "METAL",
        "Misc": "PLASTIC",  # Misc goes to Plastic bin
        "Nothing": "NOTHING",
    }
    cmd = cmd_map.get(category, "NOTHING")
    try:
        ser.write(f"{cmd}\n".encode())
        ser.flush()
    except Exception as e:
        print(f"[WARN] Serial write error: {e}")


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
display_result = [None]  # Result for GUI display (separate from cam_loop consumption)
current_frame = [None]  # Raw PIL image for main thread to display
arduino_ser = [None]  # Arduino serial connection


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

            # Store frame for main thread to display
            img = frame.to_image()
            img_display = img.resize((640, 480), Image.LANCZOS)
            current_frame[0] = img_display

            # Classify every 6 seconds (respect Groq rate limits)
            now = time.time()
            if now - last_classify >= 6.0 and not classifying:
                last_classify = now
                classifying = True

                img_small = img.resize((256, 256), Image.LANCZOS)
                buf = io.BytesIO()
                img_small.save(buf, format="JPEG", quality=60)

                t = threading.Thread(target=classify_thread, args=(buf.getvalue(),), daemon=True)
                t.start()

            # Check if classification finished
            if classifying and current_result[0] is not None:
                detected, category = current_result[0]
                current_result[0] = None
                classifying = False

                # Store for GUI display
                display_result[0] = (detected, category)

                # Send to Arduino in background
                send_to_arduino(arduino_ser[0], category)
                print(f"[CLASSIFY] {detected} -> {category}")

            time.sleep(0.03)

    container.close()


def update_gui():
    """Called from main thread to update GUI elements."""
    # Update camera frame
    if current_frame[0] is not None:
        try:
            photo = ImageTk.PhotoImage(current_frame[0])
            photo_ref[0] = photo
            cam_label.config(image=photo)
        except Exception:
            pass

    # Update classification result
    if display_result[0] is not None:
        detected, category = display_result[0]
        color = CATEGORY_COLORS.get(category, "#FFFFFF")
        status_label.config(text="● READY", fg="#44FF44")

        if category == "Nothing":
            result_label.config(text="NO E-WASTE DETECTED", fg="#555555")
            detail_label.config(text="Point camera at an e-waste item")
        else:
            result_label.config(text=f"Sort: {category.upper()}", fg=color)
            detail_label.config(text=f"Detected: {detected}")

    if running[0]:
        root.after(33, update_gui)  # ~30 FPS


def on_close():
    running[0] = False
    root.destroy()


root.protocol("WM_DELETE_WINDOW", on_close)
cam_thread = threading.Thread(target=cam_loop, daemon=True)
cam_thread.start()

print("=" * 50)
print("  E-WASTE CLASSIFIER + SORTER")
print("=" * 50)
print("Using: Groq Llama 4 Scout Vision (free)")
print("Close the window to quit.")
print("=" * 50)

# Connect to Arduino
arduino_ser[0] = connect_arduino()

# Start GUI update loop
root.after(100, update_gui)

root.mainloop()

# Cleanup
if arduino_ser[0]:
    arduino_ser[0].close()

