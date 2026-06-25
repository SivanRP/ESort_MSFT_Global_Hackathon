"""Manual P/B/M/L sender to test the Arduino alone (Phase 5).

Opens the configured serial port and lets you type a category (or its char)
to send the one-char command, so you can confirm each bin triggers without
running the whole CV pipeline.

    python scripts/serial_test.py
    python scripts/serial_test.py --port /dev/tty.usbmodem1101 --baud 115200
"""

import argparse
import sys
from pathlib import Path

# Make backend/ importable so we reuse config + the CHAR map.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import config  # noqa: E402
from serial_io import CHAR  # noqa: E402

ALIASES = {
    "p": "pcb", "pcb": "pcb",
    "b": "battery", "battery": "battery",
    "m": "metal", "metal": "metal",
    "l": "plastic", "plastic": "plastic",
}


def main():
    ap = argparse.ArgumentParser(description="Manual serial char sender")
    ap.add_argument("--port", default=config.SERIAL_PORT)
    ap.add_argument("--baud", type=int, default=config.SERIAL_BAUD)
    args = ap.parse_args()

    try:
        import serial
    except ImportError:
        print("pyserial not installed. pip install pyserial")
        return

    try:
        ser = serial.Serial(args.port, args.baud, timeout=1)
    except Exception as e:
        print(f"Could not open {args.port} @ {args.baud}: {e}")
        print("Find your port with:  ls /dev/tty.usbmodem* /dev/tty.usbserial*")
        return

    print(f"Connected to {args.port} @ {args.baud}.")
    print("Type one of: p/pcb  b/battery  m/metal  l/plastic   (q to quit)")
    try:
        while True:
            raw = input("> ").strip().lower()
            if raw in ("q", "quit", "exit"):
                break
            cls = ALIASES.get(raw)
            if not cls:
                print("  unknown. use p/b/m/l or full class name.")
                continue
            ch = CHAR[cls]
            ser.write((ch + "\n").encode())
            ser.flush()
            print(f"  sent {ch} ({cls})")
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        ser.close()
        print("\nclosed.")


if __name__ == "__main__":
    main()
