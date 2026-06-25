# E-Waste Sorter — Claude Code context

Full build context lives in [ewaste-sorter-spec.md](ewaste-sorter-spec.md). Read it before making changes.

**What this is:** a camera watches a zone, classifies one e-waste item into
`pcb | battery | metal | plastic`, waits for a stable read, then sends one
char over USB serial (`P/B/M/L`) to an Arduino that drops it in the right bin.
A React dashboard shows the live feed, tallies, and a battery HAZARD state.

**Key principle:** the serial signal fires from local code only. Event Grid
telemetry is fire-and-forget on a side path. If the network dies, the robot
still sorts. Never make the serial write depend on the socket or the cloud.

## Layout
- `backend/` — FastAPI app, camera loop, decision gate, serial, telemetry
  - `config.py` — all thresholds, port, flags (env-overridable, e.g. `ESORT_SERIAL=0`)
  - `detector.py` — YOLO26-seg inference, per-frame top detection + annotated frame
  - `decision.py` — `DecisionGate`: stability gate + commit + lockout
  - `serial_io.py` — pyserial wrapper, graceful sim-mode fallback
  - `eventgrid.py` — optional Azure telemetry (fire-and-forget)
  - `main.py` — wires it together, broadcasts per-frame JSON over `/ws`
- `frontend/` — Vite + React + Tailwind dashboard (Phase 4)
- `model/best.pt` — trained weights (produced in Colab; gitignored)
- `scripts/train.py`, `scripts/serial_test.py`

## Run the backend
```bash
cd backend
python3.11 -m venv .venv && source .venv/bin/activate
pip install -U -r requirements.txt
uvicorn main:app --reload          # add ESORT_SERIAL=0 for sim mode
```

## Conventions
- Class order is fixed in `model/data.yaml` and must match `serial_io.CHAR`.
- Tune `CONF_THRESHOLD`, `STABLE_FRAMES`, `LOCKOUT_SECONDS` in `config.py`.
- Don't train on the M1; train in Colab, run inference local with `device="mps"`.
