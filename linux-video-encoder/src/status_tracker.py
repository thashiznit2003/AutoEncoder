import threading
import time
from pathlib import Path
import re


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
        self._etas = {}
        self._smb_mounts = {}
        self._manual_files = []

    def add_event(self, message: str, level: str = "info"):
        with self._lock:
            self._events.append({"message": message, "level": level, "ts": time.time()})
            if len(self._events) > self._history_size:
                self._events = self._events[-self._history_size :]

    def start(self, src: str, dest: str, info=None, state: str = "running"):
        with self._lock:
            self._active[src] = {
                "source": src,
                "destination": dest,
                "state": state,
                "started_at": time.time(),
                "progress": 0.0,
                "info": info,
            }

    def register_proc(self, src: str, proc):
        with self._lock:
            self._procs[src] = proc

    def set_state(self, src: str, state: str):
        with self._lock:
            item = self._active.get(src)
            if item:
                item["state"] = state

    def stop_proc(self, src: str):
        with self._lock:
            proc = self._procs.pop(src, None)
            start = self._active.pop(src, None)
            eta = self._etas.pop(src, None)
        if proc:
            try:
                proc.terminate()
            except Exception:
                pass
        if start:
            self._history.append({
                "source": src,
                "destination": start.get("destination"),
                "state": "canceled",
                "finished_at": time.time(),
                "started_at": start.get("started_at"),
                "message": "Canceled by user",
                "info": start.get("info"),
                "eta_sec": eta,
                "progress": start.get("progress"),
            })
            if len(self._history) > self._history_size:
                self._history = self._history[-self._history_size :]

    def update_eta(self, src: str, eta_seconds: float):
        with self._lock:
            self._etas[src] = eta_seconds

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
                "info": start.get("info") if start else None,
                "eta_sec": self._etas.pop(src, None),
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
                        "eta_sec": self._etas.get(item.get("source")) if item.get("source") else None,
                    }
                )
            history = list(self._history)
        return {
            "active": active,
            "recent": history[::-1],  # newest first
            "timestamp": now,
        }

    def tail_logs(self, lines: int = 400):
        ansi_re = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
        try:
            data = self._log_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except FileNotFoundError:
            data = []
        filtered = []
        for line in data:
            # Skip noisy HTTP access logs
            if "GET /api/" in line or "GET / " in line:
                continue
            if "GET /favicon.ico" in line:
                continue
            filtered.append(ansi_re.sub("", line))
        if lines <= 0:
            return filtered if filtered else ["Ready to encode"]
        filtered = filtered[-lines:]
        if not filtered:
            filtered = ["Ready to encode"]
        return filtered

    def events(self):
        with self._lock:
            return list(self._events)[-self._history_size :]

    def clear_history(self, state: str = None):
        with self._lock:
            if state is None:
                self._history = []
            else:
                self._history = [h for h in self._history if h.get("state") != state]

    # SMB mount tracking helpers
    def add_smb_mount(self, mount_id: str, path: str):
        with self._lock:
            self._smb_mounts[mount_id] = path

    def remove_smb_mount(self, mount_id: str):
        with self._lock:
            self._smb_mounts.pop(mount_id, None)

    def list_smb_mounts(self):
        with self._lock:
            return dict(self._smb_mounts)

    # Manual file queue (e.g., SMB browser)
    def add_manual_file(self, path: str):
        with self._lock:
            self._manual_files.append(path)
            self._events.append({"message": f"Queued manually: {path}", "level": "info", "ts": time.time()})
            if len(self._events) > self._history_size:
                self._events = self._events[-self._history_size :]

    def consume_manual_files(self):
        with self._lock:
            items = list(self._manual_files)
            self._manual_files = []
            return items
