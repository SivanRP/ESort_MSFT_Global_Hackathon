"""pyserial wrapper with graceful, demo-safe fallback.

The serial write is the critical path: it's the one thing that actually
drives the robot. But the demo must never hard-crash because an Arduino
isn't plugged in. So if the port can't be opened we drop into sim mode and
just print what we *would* have sent. Flip ESORT_SERIAL=0 to force sim mode.
"""

CHAR = {"pcb": "P", "battery": "B", "metal": "M", "plastic": "L"}


class SerialOut:
    def __init__(self, port: str, baud: int = 115200, enabled: bool = True):
        self.port = port
        self.baud = baud
        self.enabled = enabled
        self.ser = None
        if enabled:
            try:
                import serial  # imported lazily so sim mode needs no pyserial
                self.ser = serial.Serial(port, baud, timeout=1)
                print(f"[serial] open {port} @ {baud}")
            except Exception as e:
                print(f"[serial] open failed, running in sim mode: {e}")
                self.enabled = False
        else:
            print("[serial] disabled, running in sim mode")

    def send(self, class_name: str):
        """Write the one-char command for class_name, newline-terminated.
        The Arduino reads a line at the agreed baud and maps P/B/M/L to bins."""
        ch = CHAR.get(class_name)
        if not ch:
            return
        if self.enabled and self.ser:
            try:
                self.ser.write((ch + "\n").encode())
                self.ser.flush()
                print(f"[serial] sent: {ch} ({class_name})")
            except Exception as e:
                print(f"[serial] write failed: {e}")
        else:
            print(f"[SIM] would send: {ch} ({class_name})")

    def close(self):
        if self.ser:
            try:
                self.ser.close()
            except Exception:
                pass
            self.ser = None
