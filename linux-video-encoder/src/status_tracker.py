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
        self._canceled = set()
        self._confirm_required = set()
        self._confirm_ok = set()
        self._disc_info = None
        self._disc_pending = False
        self._disc_rip_requested = False
        self._smb_pending = []
        self._usb_status = {"state": "unknown", "message": "USB status unknown"}

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
                if state != "confirm":
                    self._confirm_required.discard(src)

    def has_active(self, src: str) -> bool:
        with self._lock:
            return src in self._active

    def has_active_nonqueued(self) -> bool:
        with self._lock:
            return any(item.get("state") not in ("queued",) for item in self._active.values())

    def set_message(self, src: str, message: str):
        with self._lock:
            item = self._active.get(src)
            if item:
                item["message"] = message

    def stop_proc(self, src: str):
        with self._lock:
            proc = self._procs.pop(src, None)
            start = self._active.pop(src, None)
            eta = self._etas.pop(src, None)
            self._confirm_required.discard(src)
            self._confirm_ok.discard(src)
        if proc:
            try:
                proc.terminate()
            except Exception:
                pass
        if start:
            self._canceled.add(src)
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

    def was_canceled(self, src: str) -> bool:
        with self._lock:
            return src in self._canceled

    def clear_canceled(self, src: str):
        with self._lock:
            self._canceled.discard(src)

    # Confirmation flow
    def add_confirm_required(self, src: str):
        with self._lock:
            self._confirm_required.add(src)
            item = self._active.get(src)
            if item:
                item["state"] = "confirm"

    def is_confirm_required(self, src: str) -> bool:
        with self._lock:
            return src in self._confirm_required

    def clear_confirm_required(self, src: str):
        with self._lock:
            self._confirm_required.discard(src)

    def add_confirm_ok(self, src: str):
        with self._lock:
            self._confirm_ok.add(src)

    def is_confirm_ok(self, src: str) -> bool:
        with self._lock:
            return src in self._confirm_ok

    def clear_confirm_ok(self, src: str):
        with self._lock:
            self._confirm_ok.discard(src)

    def complete(self, src: str, success: bool, dest: str, message: str = ""):
        with self._lock:
            start = self._active.pop(src, None)
            self._procs.pop(src, None)
            self._confirm_required.discard(src)
            self._confirm_ok.discard(src)
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
            for key, item in self._active.items():
                active.append(
                    {
                        **item,
                        "duration_sec": now - item.get("started_at", now),
                        "eta_sec": self._etas.get(key),
                    }
                )
            history = list(self._history)
            disc_info = self._disc_info
            disc_pending = self._disc_pending
            usb_status = dict(self._usb_status)
        return {
            "active": active,
            "recent": history[::-1],  # newest first
            "timestamp": now,
            "disc_info": disc_info,
            "disc_pending": disc_pending,
            "usb_status": usb_status,
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

    def set_usb_status(self, state: str, message: str = ""):
        with self._lock:
            self._usb_status = {"state": state, "message": message or ""}

    def get_usb_status(self):
        with self._lock:
            return dict(self._usb_status)

    def clear_history(self, state: str = None):
        with self._lock:
            if state is None:
                self._history = []
            else:
                self._history = [h for h in self._history if h.get("state") != state]
            if state == "canceled":
                self._canceled.clear()

    # SMB mount tracking helpers
    def add_smb_mount(self, mount_id: str, path: str, label: str = None):
        with self._lock:
            entry = {"path": path}
            if label:
                entry["label"] = label
            self._smb_mounts[mount_id] = entry

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

    # Pending SMB copies (deferred until encoder idle)
    def add_smb_pending(self, entry: dict):
        with self._lock:
            self._smb_pending.append(entry)

    def pop_next_smb_pending(self):
        with self._lock:
            if not self._smb_pending:
                return None
            return self._smb_pending.pop(0)

    def has_smb_pending(self) -> bool:
        with self._lock:
            return bool(self._smb_pending)

    # Disc info/pending management
    def set_disc_info(self, info: dict):
        with self._lock:
            self._disc_info = info
            self._disc_pending = True

    def clear_disc_info(self):
        with self._lock:
            self._disc_info = None
            self._disc_pending = False
            self._disc_rip_requested = False

    def disc_info(self):
        with self._lock:
            return self._disc_info

    def disc_pending(self) -> bool:
        with self._lock:
            return self._disc_pending

    def request_disc_rip(self):
        with self._lock:
            self._disc_rip_requested = True
            self._disc_pending = True

    def consume_disc_rip_request(self) -> bool:
        with self._lock:
            req = self._disc_rip_requested
            self._disc_rip_requested = False
            return req

    def disc_rip_requested(self) -> bool:
        with self._lock:
            return self._disc_rip_requested
