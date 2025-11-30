import threading
import time
from pathlib import Path


class StatusTracker:
    """
    Thread-safe tracker for active and recent encoding tasks plus log tail access.
    """

    def __init__(self, log_path: Path, history_size: int = 100):
        self._lock = threading.Lock()
        self._active = {}
        self._history = []
        self._log_path = Path(log_path)
        self._history_size = history_size

    def start(self, src: str, dest: str):
        with self._lock:
            self._active[src] = {
                "source": src,
                "destination": dest,
                "state": "running",
                "started_at": time.time(),
            }

    def complete(self, src: str, success: bool, dest: str, message: str = ""):
        with self._lock:
            start = self._active.pop(src, None)
            record = {
                "source": src,
                "destination": dest,
                "state": "success" if success else "error",
                "finished_at": time.time(),
                "started_at": start.get("started_at") if start else None,
                "message": message,
            }
            self._history.append(record)
            if len(self._history) > self._history_size:
                self._history = self._history[-self._history_size :]

    def snapshot(self):
        now = time.time()
        with self._lock:
            active = []
            for item in self._active.values():
                active.append(
                    {
                        **item,
                        "duration_sec": now - item.get("started_at", now),
                    }
                )
            history = list(self._history)
        return {
            "active": active,
            "recent": history[::-1],  # newest first
            "timestamp": now,
        }

    def tail_logs(self, lines: int = 400):
        try:
            data = self._log_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except FileNotFoundError:
            return []
        if lines <= 0:
            return data
        return data[-lines:]
