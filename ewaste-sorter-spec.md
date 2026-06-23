# E-Waste Sorter: CV System Build Spec

This is the full build context for the computer vision + signaling software of an e-waste sorting robot, built for the Microsoft Global Hackathon (Hardware + AI track). Hand this whole file to Claude Code as project context. It also flags every step that only a human can do.

---

## 1. What this system is

A camera watches a detection zone. A person presents one e-waste item at a time. The software classifies it into one of four categories, waits until the read is stable, then sends a single character over USB serial to an Arduino. The Arduino (built by a teammate, not in this scope) moves a servo/flap to drop the item into the correct bucket. A live dashboard shows the detection, masks, confidence, running tallies, and a hazard warning for batteries.

**Categories and signal characters:**

| Category | Char | Disposal |
|----------|------|----------|
| pcb      | `P`  | recyclable |
| battery  | `B`  | hazardous |
| metal    | `M`  | recyclable |
| plastic  | `L`  | recyclable |

**Hardware reality:** no conveyor. Items are hand-fed/dropped into a zone. Host machine is an Apple Silicon M1 Mac. Arduino drops into buckets via a servo or flap.

---

## 2. Scope boundaries

**In scope (this project):** data, model training, inference, decision logic, the serial signal, the dashboard, and optional Azure Event Grid telemetry.

**Out of scope:** Arduino firmware, the physical drop mechanism, bucket placement. A teammate owns those. This project only emits a character over serial. What happens after is their problem.

---

## 3. Architecture and data flow

```
[USB/Mac camera]
      |
      v
[detector.py]  YOLO26-seg inference (device=mps), per-frame top detection + masks
      |
      v
[decision.py]  stability gate: same class, conf >= threshold, for N frames -> COMMIT
      |
      +--> [serial_io.py]   write the class char over USB to Arduino  (CRITICAL PATH)
      |
      +--> [eventgrid.py]   publish a telemetry event   (OPTIONAL, never blocks)
      |
      v
[main.py]  FastAPI, runs the camera loop, broadcasts state over WebSocket
      |
      v
[frontend]  React dashboard renders annotated frame + tallies + flair
```

**Key principle:** the serial signal fires from local code only. The cloud (Event Grid) is fire-and-forget telemetry on a side path. If the network dies, the robot still sorts.

---

## 4. Tech stack

- **Backend:** Python 3.11, `ultralytics` (YOLO26), `opencv-python`, `pyserial`, `fastapi`, `uvicorn[standard]`, `websockets`. Optional: `azure-eventgrid`, `azure-core`.
- **Frontend:** React + Vite + Tailwind. WebSocket client. Renders an annotated JPEG plus animated UI chrome.
- **Training:** Google Colab (free T4 GPU). Do NOT train on the M1; MPS training is slow and flaky. Train remote, run inference local.
- **Model:** `yolo26s-seg` (good speed/accuracy balance on M1). Fallback `yolo11s-seg` if the yolo26 weights fail to download. Run `pip install -U ultralytics` to be sure yolo26 is available.

---

## 5. Repo structure

```
ewaste-sorter/
  backend/
    main.py            # FastAPI app, camera loop, WebSocket broadcast
    detector.py        # load model, per-frame inference, top detection, annotated frame
    decision.py        # DecisionGate: stability gate + commit
    serial_io.py       # pyserial wrapper with graceful fallback
    eventgrid.py       # optional telemetry publisher
    config.py          # all thresholds, port, paths, flags
    requirements.txt
  frontend/            # Vite React app
    src/App.jsx
    src/components/
  model/
    best.pt            # trained weights (you produce this in Colab)
    data.yaml          # class names + dataset paths
  scripts/
    train.py           # or a Colab notebook
    serial_test.py     # manual P/B/M/L sender to test the Arduino alone
  README.md
  CLAUDE.md            # short context file pointing Claude Code at this spec
```

---

## 6. THE SPLIT: what only you can do vs what Claude Code builds

### Only you (Sivan) can do these. Claude Code cannot.

1. **Collect the dataset.** Physically photograph 150-300 of the real items you'll demo with, on the real surface and lighting. Claude Code cannot hold a camera.
2. **Annotate in Roboflow.** Draw polygon masks for each of the 4 classes. Manual clicking. Cannot be automated.
3. **Run the Colab training.** Your Google account, your GPU runtime, your Roboflow API key. Claude Code writes the notebook but cannot execute Colab for you.
4. **Grant Mac camera permission.** macOS will block the camera until you allow your terminal/IDE under System Settings > Privacy & Security > Camera. This silently breaks things if skipped.
5. **Plug in the Arduino and find the port.** Run `ls /dev/tty.usbmodem* /dev/tty.usbserial*` and put the result in `config.py`.
6. **Agree the serial protocol with your Arduino teammate.** Confirm baud (use 115200) and that they read a line and map `P/B/M/L` to bins.
7. **Provision Azure Event Grid (only if doing the optional flex).** Create a custom topic, copy the endpoint + access key into env vars. Use a personal or hackathon subscription.
8. **Tune thresholds and rehearse.** Test with real objects, adjust the gate, run the demo 5 times.

### Claude Code builds all of this.

- Entire backend (`main.py`, `detector.py`, `decision.py`, `serial_io.py`, `eventgrid.py`, `config.py`, `requirements.txt`).
- The React dashboard.
- The training script / Colab notebook and `data.yaml`.
- `serial_test.py`.
- `README.md` and `CLAUDE.md`.
- Installing deps, running the server, debugging, iterating.

---

## 7. Step-by-step phases

Each phase lists the owner, the steps, exact commands, and a "done when" check.

### Phase 0: Repo + environment (Claude Code, then you)

**Claude Code:**
- Scaffold the repo structure above.
- Create `backend/requirements.txt`:
  ```
  ultralytics
  opencv-python
  pyserial
  fastapi
  uvicorn[standard]
  websockets
  azure-eventgrid
  azure-core
  ```
- Create a Python venv and install.

**You:**
```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -U -r requirements.txt
```
**Done when:** `python -c "from ultralytics import YOLO; print('ok')"` prints ok.

---

### Phase 1: Data (you, mostly)

**You:**
1. Create a Roboflow project, Instance Segmentation type, 4 classes: `pcb`, `battery`, `metal`, `plastic`.
2. Pull a few starter images from Roboflow Universe (search "e-waste", "pcb", "battery") to cold-start.
3. Photograph 150-300 of your actual demo items. Vary angle and position. Use the same lighting/surface you'll demo on.
4. Annotate every image with polygon masks.
5. Add augmentation in Roboflow (flip, rotate, brightness, blur). Generate a version.
6. Export in **YOLOv8 segmentation** format (compatible with yolo26). Copy your Roboflow API/download snippet.

**Done when:** you have a Roboflow dataset version exported with a `data.yaml` and train/valid/test splits.

---

### Phase 2: Training (Claude Code writes, you run)

**Claude Code:** write `scripts/train.py` (or a Colab notebook) that:
- installs ultralytics,
- downloads the Roboflow dataset via API key,
- trains `yolo26s-seg.pt` and exports `best.pt`.

Training command core:
```bash
yolo task=segment mode=train model=yolo26s-seg.pt data=data.yaml epochs=100 imgsz=640 batch=-1
```
Or in Python:
```python
from ultralytics import YOLO
model = YOLO("yolo26s-seg.pt")
model.train(data="data.yaml", epochs=100, imgsz=640, batch=-1)
```

**You:**
- Open the notebook in **Colab**, set runtime to GPU (T4), paste your Roboflow key, run all.
- Download the resulting `runs/segment/train/weights/best.pt`.
- Drop it in `model/best.pt` in the repo.

**Done when:** `best.pt` exists locally and the Colab run shows mAP improving (aim for mAP50 > 0.7 on your val set; if lower, add more data for the weak class).

---

### Phase 3: Inference + decision + serial backend (Claude Code builds, you test)

**Claude Code:** build the backend. Implementation specifics below in Section 8. Core behavior:
- Load `model/best.pt` with `device="mps"`.
- Run `model.track(source=CAMERA_INDEX, stream=True, persist=True, conf=0.5, device="mps")`.
- Per frame: take the highest-confidence detection as the candidate, get an annotated frame via `result.plot()`.
- Feed candidate into `DecisionGate`. On commit, call `serial_io.send(class_name)` and (optionally) `eventgrid.publish(...)`.
- Broadcast per-frame state over WebSocket.

**You:**
- Grant camera permission (Phase 0 reminder).
- Run the server: `uvicorn main:app --reload` from `backend/`.
- Hold items in view, confirm the terminal prints commits with the right char.

**Done when:** presenting a battery prints a committed `B` once (not repeatedly), and removing/replacing items re-arms cleanly.

---

### Phase 4: Dashboard (Claude Code builds)

**Claude Code:** build the React dashboard.
- Connect to the backend WebSocket.
- Render the annotated frame (`<img>` from base64 JPEG).
- Show 4 category tally cards that pulse when incremented.
- Show current top detection class + an animated confidence ring.
- Show a "SORTED -> bin X" flash on each commit.
- Battery gets a pulsing red HAZARD state.
- Corner FPS/latency counter.
- Dark theme, neon accents.

**You:** `npm run dev` in `frontend/`, open the page, watch it update live.

**Done when:** the dashboard mirrors detections in real time and the chrome animates on commit.

---

### Phase 5: Arduino integration (you + teammate, Claude Code provides the test tool)

**Claude Code:** write `scripts/serial_test.py` that opens the configured port and lets you type `P/B/M/L` to send the char, so you can test the Arduino without the full pipeline.

**You + teammate:**
1. Plug in Arduino, find the port (`ls /dev/tty.usbmodem*`), set `SERIAL_PORT` in `config.py`.
2. Confirm teammate's firmware reads a line at 115200 and maps each char to a servo position.
3. Run `python scripts/serial_test.py`, send each char, confirm the right bucket triggers.
4. Then run the full backend and confirm end-to-end: item in -> detection -> servo moves.

**Done when:** each of the 4 chars drives the correct physical bin, both from the test script and the live pipeline.

---

### Phase 6: Event Grid telemetry (optional flex; Claude Code builds, you provision)

Only do this if Phases 1-5 are solid. It is the Microsoft architecture story, not core function.

**You:**
- In Azure, create an Event Grid custom topic. Copy the topic endpoint and an access key.
- Set env vars: `EVENTGRID_TOPIC_ENDPOINT`, `EVENTGRID_TOPIC_KEY`.

**Claude Code:** build `eventgrid.py` to publish a small event on each commit (class, confidence, timestamp). Call it async/fire-and-forget so it never delays the serial write. Wrap in try/except so a cloud failure is silent.

**Done when:** commits appear as events in Event Grid, and pulling the network cable does not stop the sorter.

---

### Phase 7: Polish and rehearsal (you)

- Tune `CONF_THRESHOLD`, `STABLE_FRAMES`, `LOCKOUT_SECONDS` against real items.
- Fix the worst-performing class with more training images if needed.
- Rehearse the full demo 5 times. Lead the pitch with the lithium-battery fire hazard angle.

---

## 8. Implementation specifics (reference snippets)

These are the genuinely tricky bits. Give them to Claude Code as the intended behavior; it can expand and harden them.

### config.py
```python
CAMERA_INDEX = 0
MODEL_PATH = "../model/best.pt"
DEVICE = "mps"            # Apple Silicon. use "cpu" if mps misbehaves.

CONF_THRESHOLD = 0.6     # min confidence to count a frame as a candidate
STABLE_FRAMES = 8        # consecutive matching frames required to commit
LOCKOUT_SECONDS = 1.5    # cooldown after a commit, prevents double-fire

SERIAL_ENABLED = True
SERIAL_PORT = "/dev/tty.usbmodemXXXX"   # set after `ls /dev/tty.usbmodem*`
SERIAL_BAUD = 115200

EVENTGRID_ENABLED = False
```

### decision.py (the stability gate, the part you were worried about)
```python
from collections import deque
import time

class DecisionGate:
    def __init__(self, conf, stable_frames, lockout):
        self.conf = conf
        self.stable_frames = stable_frames
        self.lockout = lockout
        self.history = deque(maxlen=stable_frames)
        self.last_commit_t = 0.0

    def update(self, top_class, top_conf):
        """Call once per frame with the highest-confidence detection
        (top_class=None if nothing detected). Returns the committed
        class name once when a stable read locks in, else None."""
        now = time.time()
        candidate = top_class if (top_class and top_conf >= self.conf) else None
        self.history.append(candidate)

        if now - self.last_commit_t < self.lockout:
            return None

        if (len(self.history) == self.stable_frames
                and candidate is not None
                and all(c == candidate for c in self.history)):
            self.last_commit_t = now
            self.history.clear()
            return candidate
        return None
```

### serial_io.py (graceful, demo-safe)
```python
import serial

CHAR = {"pcb": "P", "battery": "B", "metal": "M", "plastic": "L"}

class SerialOut:
    def __init__(self, port, baud=115200, enabled=True):
        self.enabled = enabled
        self.ser = None
        if enabled:
            try:
                self.ser = serial.Serial(port, baud, timeout=1)
            except Exception as e:
                print("serial open failed, running in sim mode:", e)
                self.enabled = False

    def send(self, class_name):
        ch = CHAR.get(class_name)
        if not ch:
            return
        if self.enabled and self.ser:
            try:
                self.ser.write((ch + "\n").encode())
            except Exception as e:
                print("serial write failed:", e)
        else:
            print(f"[SIM] would send: {ch}")
```

### detector.py (per-frame extraction)
```python
from ultralytics import YOLO

class Detector:
    def __init__(self, model_path, device="mps", conf=0.5):
        self.model = YOLO(model_path)
        self.device = device
        self.conf = conf

    def stream(self, source):
        # yields (annotated_bgr_frame, top_class_name_or_None, top_conf)
        for r in self.model.track(source=source, stream=True, persist=True,
                                   conf=self.conf, device=self.device, verbose=False):
            annotated = r.plot()  # draws masks + labels for free
            top_class, top_conf = None, 0.0
            if r.boxes is not None and len(r.boxes) > 0:
                confs = r.boxes.conf.tolist()
                i = max(range(len(confs)), key=lambda k: confs[k])
                top_conf = confs[i]
                top_class = self.model.names[int(r.boxes.cls[i])]
            yield annotated, top_class, top_conf
```

### main.py (camera loop + WebSocket, shape)
- One background task iterates `Detector.stream`, runs `DecisionGate.update`, and on a commit calls `SerialOut.send` and optional `eventgrid.publish`.
- Each frame: JPEG-encode the annotated frame, base64 it, and broadcast a JSON message to all connected WebSocket clients:
```json
{
  "frame": "<base64 jpeg>",
  "top_class": "battery",
  "top_conf": 0.91,
  "committed": "battery",
  "tallies": {"pcb": 3, "battery": 1, "metal": 2, "plastic": 5},
  "fps": 18.4
}
```
- `committed` is non-null only on the frame a commit happens, so the UI can flash.

### eventgrid.py (optional)
```python
import os
from azure.eventgrid import EventGridPublisherClient, EventGridEvent
from azure.core.credentials import AzureKeyCredential

def make_client():
    endpoint = os.environ["EVENTGRID_TOPIC_ENDPOINT"]
    key = os.environ["EVENTGRID_TOPIC_KEY"]
    return EventGridPublisherClient(endpoint, AzureKeyCredential(key))

def publish(client, class_name, conf):
    try:
        client.send([EventGridEvent(
            subject="ewaste/sort",
            event_type="EwasteSorted",
            data={"category": class_name, "confidence": conf},
            data_version="1.0",
        )])
    except Exception as e:
        print("eventgrid publish failed (ignored):", e)
```
Call this in a thread or async task so it never blocks the serial write.

---

## 9. Parameters to tune (Phase 7)

| Param | Start | Raise it if... | Lower it if... |
|-------|-------|----------------|----------------|
| CONF_THRESHOLD | 0.6 | false detections fire | real items get ignored |
| STABLE_FRAMES | 8 | it commits too eagerly | it feels laggy to commit |
| LOCKOUT_SECONDS | 1.5 | one item double-fires | items come fast and get missed |

---

## 10. Demo-day checklist

- [ ] Camera permission granted to the IDE/terminal
- [ ] `model/best.pt` present and loads
- [ ] All 4 classes detect reliably under demo lighting
- [ ] Serial port correct in config, all 4 chars drive correct bins
- [ ] Dashboard runs full-screen on a second display
- [ ] Battery shows the HAZARD state (your pitch hook)
- [ ] Backup plan: `--no-serial` sim mode works if the Arduino fails live
- [ ] Pitch opens with the lithium-battery fire problem, not "we sort trash"

---

## 11. First prompt to give Claude Code

> Read `ewaste-sorter-spec.md`. Scaffold the repo per Section 5. Build the Phase 3 backend first: `config.py`, `detector.py`, `decision.py`, `serial_io.py`, and a `main.py` FastAPI app that runs the camera loop, applies the DecisionGate, sends the serial char on commit, and broadcasts the per-frame JSON from Section 8 over a WebSocket. Use the snippets in Section 8 as the intended behavior. Make serial and event grid optional via config flags. Then we'll do the dashboard.

Build the backend before the dashboard. A working detect-and-signal loop is the core. The dashboard makes it stunning, but only after the core works.
