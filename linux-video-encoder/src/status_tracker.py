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
        self._events = []
        self._procs = {}
        self._log_path = Path(log_path)
        self._history_size = history_size

    def add_event(self, message: str, level: str = "info"):
        with self._lock:
            self._events.append({"message": message, "level": level, "ts": time.time()})
            if len(self._events) > self._history_size:
                self._events = self._events[-self._history_size :]

    def start(self, src: str, dest: str):
        with self._lock:
            self._active[src] = {
                "source": src,
                "destination": dest,
                "state": "running",
                "started_at": time.time(),
                "progress": 0.0,
            }

    def register_proc(self, src: str, proc):
        with self._lock:
            self._procs[src] = proc

    def stop_proc(self, src: str):
        with self._lock:
            proc = self._procs.pop(src, None)
        if proc:
            try:
                proc.terminate()
            except Exception:
                pass

    def complete(self, src: str, success: bool, dest: str, message: str = ""):
        with self._lock:
            start = self._active.pop(src, None)
            self._procs.pop(src, None)
            record = {
                "source": src,
                "destination": dest,
                "state": "success" if success else "error",
                "finished_at": time.time(),
                "started_at": start.get("started_at") if start else None,
                "message": message,
                "progress": 100.0 if success else start.get("progress") if start else None,
            }
            self._history.append(record)
            if len(self._history) > self._history_size:
                self._history = self._history[-self._history_size :]

    def update_progress(self, src: str, progress: float):
        with self._lock:
            item = self._active.get(src)
            if item:
                item["progress"] = max(0.0, min(100.0, progress))

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
        filtered = []
        for line in data:
            # Skip noisy HTTP access logs
            if "GET /api/" in line or "GET / " in line:
                continue
            if "GET /favicon.ico" in line:
                continue
            filtered.append(line)
        if lines <= 0:
            return filtered
        return filtered[-lines:]

    def events(self):
        with self._lock:
            return list(self._events)[-self._history_size :]

    def clear_history(self, state: str = None):
        with self._lock:
            if state is None:
                self._history = []
            else:
                self._history = [h for h in self._history if h.get("state") != state]
