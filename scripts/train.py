"""Train yolo26s-seg on the Roboflow e-waste dataset (Phase 2).

Designed to be pasted/run in Google Colab on a T4 GPU. Do NOT train on the
M1 (MPS training is slow and flaky) — train remote, run inference local.

Colab steps:
  1. Runtime > Change runtime type > GPU (T4).
  2. Set ROBOFLOW_API_KEY below (or as an env var / Colab secret).
  3. Fill in WORKSPACE / PROJECT / VERSION from your Roboflow "Export" snippet.
  4. Run all. Download runs/segment/train/weights/best.pt and drop it in
     model/best.pt in this repo.

Done when best.pt exists locally and mAP50 > 0.7 on your val set.
"""

import os

# yolo26s-seg is the target; falls back to yolo11s-seg if the weights for
# yolo26 fail to download (run `pip install -U ultralytics` to be sure).
BASE_MODEL = "yolo26s-seg.pt"
FALLBACK_MODEL = "yolo11s-seg.pt"

EPOCHS = 100
IMGSZ = 640
BATCH = -1  # auto-batch to fit GPU memory

# --- Roboflow dataset (fill these in from your Export snippet) -------------
ROBOFLOW_API_KEY = os.getenv("ROBOFLOW_API_KEY", "PASTE_YOUR_KEY")
WORKSPACE = "your-workspace"
PROJECT = "ewaste-sorter"
VERSION = 1


def install():
    # In Colab these run as shell installs; harmless to call locally too.
    os.system("pip install -U ultralytics roboflow")


def download_dataset() -> str:
    """Download the dataset and return the path to its data.yaml."""
    from roboflow import Roboflow

    rf = Roboflow(api_key=ROBOFLOW_API_KEY)
    project = rf.workspace(WORKSPACE).project(PROJECT)
    # YOLOv8 segmentation export is compatible with yolo26.
    dataset = project.version(VERSION).download("yolov8")
    return os.path.join(dataset.location, "data.yaml")


def train(data_yaml: str):
    from ultralytics import YOLO

    try:
        model = YOLO(BASE_MODEL)
    except Exception as e:
        print(f"{BASE_MODEL} unavailable ({e}); falling back to {FALLBACK_MODEL}")
        model = YOLO(FALLBACK_MODEL)

    model.train(
        data=data_yaml,
        task="segment",
        epochs=EPOCHS,
        imgsz=IMGSZ,
        batch=BATCH,
    )
    print("Done. Weights at runs/segment/train/weights/best.pt")


if __name__ == "__main__":
    install()
    data_yaml = download_dataset()
    train(data_yaml)
