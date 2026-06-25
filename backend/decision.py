"""The stability gate.

A single detection frame is noisy: confidence flickers, the model may
flip classes for a frame, a hand passing through can register junk. The
DecisionGate turns that noisy per-frame stream into one clean COMMIT per
presented item:

  * a frame "counts" only if it has a class at/above the confidence floor
  * we commit only when the last N frames all agree on the same class
  * after a commit we ignore everything for LOCKOUT_SECONDS so one item
    can't double-fire while it lingers in view

Returns the committed class name exactly once per item, else None.
"""

from collections import deque
import time


class DecisionGate:
    def __init__(self, conf: float, stable_frames: int, lockout: float):
        self.conf = conf
        self.stable_frames = stable_frames
        self.lockout = lockout
        self.history = deque(maxlen=stable_frames)
        self.last_commit_t = 0.0
        # How many of the most recent frames agree on the current candidate.
        # Exposed purely so the dashboard can draw a "locking in..." progress.
        self.streak = 0

    def update(self, top_class, top_conf):
        """Call once per frame with the highest-confidence detection
        (top_class=None if nothing detected). Returns the committed
        class name once when a stable read locks in, else None."""
        now = time.time()
        candidate = top_class if (top_class and top_conf >= self.conf) else None
        self.history.append(candidate)
        self._recompute_streak()

        # Cooldown: swallow everything (but keep tracking history) so a single
        # item dwelling in frame doesn't fire repeatedly.
        if now - self.last_commit_t < self.lockout:
            return None

        if (
            len(self.history) == self.stable_frames
            and candidate is not None
            and all(c == candidate for c in self.history)
        ):
            self.last_commit_t = now
            self.history.clear()
            self.streak = 0
            return candidate
        return None

    def _recompute_streak(self):
        """Count trailing frames that match the most recent candidate."""
        latest = self.history[-1] if self.history else None
        if latest is None:
            self.streak = 0
            return
        count = 0
        for c in reversed(self.history):
            if c == latest:
                count += 1
            else:
                break
        self.streak = count

    def progress(self) -> float:
        """0.0 -> 1.0 fraction of the way to a commit, for UI feedback."""
        if self.stable_frames <= 0:
            return 0.0
        return min(self.streak / self.stable_frames, 1.0)

    def in_lockout(self) -> bool:
        return (time.time() - self.last_commit_t) < self.lockout

    def reset(self):
        """Clear all state and re-arm immediately (used by /reset)."""
        self.history.clear()
        self.last_commit_t = 0.0
        self.streak = 0
