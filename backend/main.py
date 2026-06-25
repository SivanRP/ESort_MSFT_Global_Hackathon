"""FastAPI app: camera loop + DecisionGate + serial + WebSocket broadcast.

Architecture
------------
The YOLO tracker is a blocking generator, so the camera loop runs on its own
daemon thread (``detection_loop``). For each frame it:

  1. asks the DecisionGate whether this frame commits a class
  2. on commit -> fires the serial char (critical path) + optional telemetry
  3. JPEG-encodes the annotated frame and broadcasts the per-frame JSON to
     every connected WebSocket client

WebSockets are async and the camera loop is a thread, so we hop back onto the
event loop with ``run_coroutine_threadsafe`` to broadcast. The serial signal
never depends on the socket or the cloud — if either dies, the robot keeps
sorting.

Run:
    cd backend && uvicorn main:app --reload
    ESORT_SERIAL=0 uvicorn main:app          # sim mode, no Arduino
"""

import asyncio
import base64
import threading
import time

import cv2
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

import config
from decision import DecisionGate
from eventgrid import EventGrid
from serial_io import SerialOut

app = FastAPI(title="E-Waste Sorter")

# The Vite dev server runs on a different origin; allow it to connect.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------------------------------
# WebSocket connection manager
# --------------------------------------------------------------------------
class ConnectionManager:
    def __init__(self):
        self.active: set[WebSocket] = set()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.add(ws)

    def disconnect(self, ws: WebSocket):
        self.active.discard(ws)

    async def broadcast(self, message: dict):
        dead = []
        for ws in list(self.active):
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.active.discard(ws)


manager = ConnectionManager()


# --------------------------------------------------------------------------
# Shared runtime state (written by the camera thread, read by HTTP/WS)
# --------------------------------------------------------------------------
class State:
    def __init__(self):
        self.tallies = {c: 0 for c in config.CLASSES}
        self.latest_message: dict | None = None
        self.status = "starting"          # starting | running | error
        self.error: str | None = None
        self.lock = threading.Lock()

    def snapshot_tallies(self):
        with self.lock:
            return dict(self.tallies)


state = State()

# Wired up at startup.
gate = DecisionGate(config.CONF_THRESHOLD, config.STABLE_FRAMES, config.LOCKOUT_SECONDS)
serial_out: SerialOut | None = None
eventgrid: EventGrid | None = None

_loop: asyncio.AbstractEventLoop | None = None
_stop = threading.Event()
_thread: threading.Thread | None = None


# --------------------------------------------------------------------------
# Broadcast helper: schedule the async broadcast from the camera thread
# --------------------------------------------------------------------------
def _broadcast(message: dict):
    with state.lock:
        state.latest_message = message
    if _loop is None or not manager.active:
        return
    asyncio.run_coroutine_threadsafe(manager.broadcast(message), _loop)


def _encode_frame(frame) -> str:
    ok, buf = cv2.imencode(
        ".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), config.JPEG_QUALITY]
    )
    if not ok:
        return ""
    return base64.b64encode(buf).decode("ascii")


def _build_message(frame_b64, top_class, top_conf, committed, fps) -> dict:
    return {
        "frame": frame_b64,
        "top_class": top_class,
        "top_conf": round(float(top_conf), 3),
        "committed": committed,                 # non-null only on the commit frame
        "tallies": state.snapshot_tallies(),
        "fps": round(fps, 1),
        # extra fields the dashboard can use; harmless to ignore
        "stability": round(gate.progress(), 3),
        "in_lockout": gate.in_lockout(),
        "hazard": (top_class in config.HAZARD_CLASSES) if top_class else False,
        "status": "running",
    }


# --------------------------------------------------------------------------
# The camera loop (runs on its own thread)
# --------------------------------------------------------------------------
def detection_loop():
    global serial_out, eventgrid
    # Import Detector lazily so the server can still boot (and report the
    # error to the dashboard) if ultralytics/torch or the model is missing.
    try:
        from detector import Detector

        detector = Detector(
            config.MODEL_PATH, device=config.DEVICE, conf=config.DETECTOR_CONF
        )
        print(f"[detector] loaded {config.MODEL_PATH} on {config.DEVICE}")
    except Exception as e:
        msg = f"failed to load model: {e}"
        print(f"[detector] {msg}")
        with state.lock:
            state.status = "error"
            state.error = msg
        _broadcast({"status": "error", "error": msg})
        return

    with state.lock:
        state.status = "running"

    fps = 0.0
    last_t = time.time()
    try:
        for annotated, top_class, top_conf in detector.stream(config.CAMERA_INDEX):
            if _stop.is_set():
                break

            committed = gate.update(top_class, top_conf)
            if committed:
                # CRITICAL PATH first: drive the robot.
                serial_out.send(committed)
                with state.lock:
                    state.tallies[committed] = state.tallies.get(committed, 0) + 1
                # Side path, fire-and-forget telemetry.
                eventgrid.publish(committed, top_conf)
                print(f"[commit] {committed} (conf={top_conf:.2f})")

            # FPS as an exponential moving average for a steady readout.
            now = time.time()
            dt = now - last_t
            last_t = now
            if dt > 0:
                inst = 1.0 / dt
                fps = inst if fps == 0 else (0.9 * fps + 0.1 * inst)

            frame_b64 = _encode_frame(annotated)
            _broadcast(_build_message(frame_b64, top_class, top_conf, committed, fps))
    except Exception as e:
        msg = f"camera loop crashed: {e}"
        print(f"[detector] {msg}")
        with state.lock:
            state.status = "error"
            state.error = msg
        _broadcast({"status": "error", "error": msg})


# --------------------------------------------------------------------------
# Lifecycle
# --------------------------------------------------------------------------
@app.on_event("startup")
async def on_startup():
    global _loop, serial_out, eventgrid, _thread
    _loop = asyncio.get_running_loop()
    serial_out = SerialOut(
        config.SERIAL_PORT, config.SERIAL_BAUD, enabled=config.SERIAL_ENABLED
    )
    eventgrid = EventGrid(enabled=config.EVENTGRID_ENABLED)
    _stop.clear()
    _thread = threading.Thread(target=detection_loop, name="camera-loop", daemon=True)
    _thread.start()


@app.on_event("shutdown")
async def on_shutdown():
    _stop.set()
    if _thread:
        _thread.join(timeout=5)
    if serial_out:
        serial_out.close()


# --------------------------------------------------------------------------
# HTTP + WebSocket endpoints
# --------------------------------------------------------------------------
@app.get("/")
async def root():
    return {
        "name": "E-Waste Sorter backend",
        "status": state.status,
        "error": state.error,
        "tallies": state.snapshot_tallies(),
        "serial_enabled": serial_out.enabled if serial_out else None,
        "eventgrid_enabled": eventgrid.enabled if eventgrid else None,
        "ws": "/ws",
    }


@app.get("/health")
async def health():
    return {"status": state.status, "error": state.error}


@app.post("/reset")
async def reset():
    """Re-arm the gate and zero the tallies (handy between demo runs)."""
    gate.reset()
    with state.lock:
        for k in state.tallies:
            state.tallies[k] = 0
    return {"ok": True, "tallies": state.snapshot_tallies()}


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await manager.connect(ws)
    # Send the most recent frame immediately so a fresh client isn't blank.
    with state.lock:
        latest = state.latest_message
    if latest:
        try:
            await ws.send_json(latest)
        except Exception:
            pass
    try:
        # We don't expect inbound messages; this keeps the socket open and
        # lets us notice disconnects.
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)
    except Exception:
        manager.disconnect(ws)
