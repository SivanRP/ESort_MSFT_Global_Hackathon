# E-Waste Sorter

Computer-vision + signaling software for an e-waste sorting robot
(Microsoft Global Hackathon — Hardware + AI track).

A camera watches a detection zone. A person presents one item at a time. The
software classifies it into one of four categories, waits until the read is
stable, then sends a single character over USB serial to an Arduino, which
moves a servo/flap to drop the item into the correct bucket. A live dashboard
shows the detection, masks, confidence, running tallies, and a battery hazard
warning.

| Category | Char | Disposal   |
|----------|------|------------|
| pcb      | `P`  | recyclable |
| battery  | `B`  | hazardous  |
| metal    | `M`  | recyclable |
| plastic  | `L`  | recyclable |

> **Why it matters:** lithium batteries tossed in the wrong bin start fires in
> recycling facilities. Reliable battery detection is the pitch.

## Architecture

```
[camera] -> detector.py (YOLO26-seg, mps) -> decision.py (stability gate)
              -> serial_io.py  (USB char to Arduino, CRITICAL PATH)
              -> eventgrid.py  (telemetry, OPTIONAL, never blocks)
         main.py (FastAPI) broadcasts per-frame JSON over /ws -> React dashboard
```

The serial signal fires from local code only. The cloud is fire-and-forget
telemetry on a side path. **If the network dies, the robot still sorts.**

## Repo layout

```
backend/    FastAPI app, camera loop, decision gate, serial, telemetry
frontend/   Vite + React + Tailwind dashboard (Phase 4)
model/      best.pt (trained in Colab) + data.yaml
scripts/    train.py (Colab), serial_test.py (manual Arduino test)
```

## Quick start (backend)

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -U -r requirements.txt

# Grant camera permission to your terminal/IDE:
#   System Settings > Privacy & Security > Camera
# Set the serial port in config.py after:  ls /dev/tty.usbmodem*

uvicorn main:app --reload
```

- WebSocket stream: `ws://localhost:8000/ws`
- Status: `GET http://localhost:8000/` · Health: `/health` · Reset tallies: `POST /reset`

### Sim mode (no Arduino)

```bash
ESORT_SERIAL=0 uvicorn main:app --reload
```

Commits print `[SIM] would send: B (battery)` instead of writing to serial.

### Useful config overrides (env vars)

| Var | Meaning |
|-----|---------|
| `ESORT_SERIAL=0` | force sim mode |
| `ESORT_DEVICE=cpu` | if MPS misbehaves |
| `ESORT_CAMERA=1` | pick a different camera index |
| `ESORT_CONF=0.6` | gate confidence floor |
| `ESORT_STABLE=8` | consecutive frames to commit |
| `ESORT_LOCKOUT=1.5` | post-commit cooldown (s) |
| `ESORT_EVENTGRID=1` | enable Azure telemetry (needs topic env vars) |

## Per-frame WebSocket message

```json
{
  "frame": "<base64 jpeg>",
  "top_class": "battery",
  "top_conf": 0.91,
  "committed": "battery",
  "tallies": {"pcb": 3, "battery": 1, "metal": 2, "plastic": 5},
  "fps": 18.4,
  "stability": 0.75,
  "in_lockout": false,
  "hazard": true,
  "status": "running"
}
```

`committed` is non-null only on the frame a commit happens, so the UI can flash.

## Model

Train in Google Colab (free T4 GPU) — see `scripts/train.py`. Export
`best.pt` and drop it in `model/best.pt`. Do **not** train on the M1; run
inference locally with `device="mps"`. Until `best.pt` exists, the backend
boots and reports `status: error` over the socket so the dashboard can show it.

## Quick start (dashboard)

In a second terminal (leave the backend running):

```bash
cd frontend
npm install
npm run dev
```

Open the printed URL (default http://localhost:5173). The dashboard connects to
the backend WebSocket automatically and shows: the annotated live feed, an
animated confidence ring, the 4 tally cards (which pop on each commit), a
`SORTED → BIN X` flash, a pulsing battery HAZARD state, and an FPS counter.
Until `model/best.pt` exists it shows a `NO MODEL` state — that's expected.

To point it at a backend on another host: `VITE_WS_URL=ws://HOST:8000/ws npm run dev`.

## Status

- [x] Phase 3 — inference + decision + serial backend
- [x] Phase 4 — React dashboard
- [ ] Phase 5 — Arduino integration
- [ ] Phase 6 — Event Grid telemetry (optional)

See [ewaste-sorter-spec.md](ewaste-sorter-spec.md) for the full phase plan.
