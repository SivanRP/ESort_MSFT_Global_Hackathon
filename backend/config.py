"""Central configuration for the e-waste sorter backend.

Every threshold, port, path, and feature flag lives here. The flagged
values (serial, event grid) can also be overridden with environment
variables so you can flip to sim mode at the demo without editing code:

    ESORT_SERIAL=0      uvicorn main:app      # force sim mode, no Arduino
    ESORT_DEVICE=cpu    uvicorn main:app      # if mps misbehaves
"""

import os
from pathlib import Path

# --- paths -----------------------------------------------------------------
# Resolve against the repo layout (backend/ + model/) instead of the cwd so
# the server works no matter where uvicorn is launched from.
BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = os.getenv("ESORT_MODEL", str(BASE_DIR / "model" / "best.pt"))


# --- helpers ---------------------------------------------------------------
def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    return int(raw) if raw is not None else default


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    return float(raw) if raw is not None else default


# --- camera / model --------------------------------------------------------
CAMERA_INDEX = _env_int("ESORT_CAMERA", 0)
DEVICE = os.getenv("ESORT_DEVICE", "mps")   # Apple Silicon. use "cpu" if mps misbehaves.

# Loose gate at the model so borderline frames still reach the DecisionGate,
# which applies the stricter CONF_THRESHOLD below.
DETECTOR_CONF = _env_float("ESORT_DETECTOR_CONF", 0.5)

# --- decision gate ---------------------------------------------------------
CONF_THRESHOLD = _env_float("ESORT_CONF", 0.6)    # min confidence to count a frame as a candidate
STABLE_FRAMES = _env_int("ESORT_STABLE", 8)        # consecutive matching frames required to commit
LOCKOUT_SECONDS = _env_float("ESORT_LOCKOUT", 1.5) # cooldown after a commit, prevents double-fire

# --- serial ----------------------------------------------------------------
SERIAL_ENABLED = _env_bool("ESORT_SERIAL", True)
SERIAL_PORT = os.getenv("ESORT_SERIAL_PORT", "/dev/tty.usbmodemXXXX")  # set after `ls /dev/tty.usbmodem*`
SERIAL_BAUD = _env_int("ESORT_SERIAL_BAUD", 115200)

# --- event grid (optional telemetry) --------------------------------------
EVENTGRID_ENABLED = _env_bool("ESORT_EVENTGRID", False)
# Endpoint + key are read from EVENTGRID_TOPIC_ENDPOINT / EVENTGRID_TOPIC_KEY
# inside eventgrid.py, per the spec.

# --- streaming -------------------------------------------------------------
JPEG_QUALITY = _env_int("ESORT_JPEG_QUALITY", 70)  # 0-100, lower = smaller frames over the socket

# --- categories ------------------------------------------------------------
# Canonical class order; mirrors model/data.yaml. Used to seed tallies so the
# dashboard always has all four cards even before anything is detected.
CLASSES = ["pcb", "battery", "metal", "plastic"]
HAZARD_CLASSES = {"battery"}
