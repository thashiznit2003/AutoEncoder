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
        self._rename = {}
        self._smb_mounts = {}
        self._manual_files = []
        self._canceled = set()
        self._confirm_required = set()
        self._confirm_ok = set()
        self._disc_info = None
        self._disc_info_cache = None
        self._disc_info_cache_key = None
        self._disc_pending = False
        self._disc_rip_requested = False
        self._disc_rip_mode = None
        self._disc_rip_blocked = False
        self._disc_scan_paused = False
        self._disc_preserve_info = False
        self._disc_present = None
        self._disc_auto_queue = []
        self._disc_auto_key = None
        self._disc_auto_complete_key = None
        self._disc_key = None
        self._smb_pending = []
        self._usb_status = {"state": "unknown", "message": "USB status unknown"}
        self._disc_scan_inflight = False
        self._disc_scan_cooldown_until = 0.0
        self._disc_scan_failures = 0
        self._disc_scan_last_ts = 0.0
        self._disc_scan_started_ts = None
        self._disc_scan_last_duration = None
        self._disc_scan_last_timed_out = None
        self._disc_inserted_ts = None
        self._disc_removed_ts = None
        self._disc_info_first_ts = None
        self._disc_titles_first_ts = None
        self._disc_info_last_ts = None
        self._disc_titles_last_ts = None
        self._disc_info_cleared_ts = None
        self._disc_titles_cleared_ts = None
        self._disc_label_first_ts = None
        self._disc_label_last_ts = None
        self._disc_label_cleared_ts = None

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

    def set_rename(self, src: str, name: str):
        with self._lock:
            self._rename[src] = name
            item = self._active.get(src)
            if item:
                item["rename_to"] = name

    def get_rename(self, src: str):
        with self._lock:
            return self._rename.get(src)

    def clear_rename(self, src: str):
        with self._lock:
            self._rename.pop(src, None)
            item = self._active.get(src)
            if item and "rename_to" in item:
                item.pop("rename_to", None)

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

    def update_destination(self, src: str, dest: str):
        with self._lock:
            item = self._active.get(src)
            if item:
                item["destination"] = dest

    def update_fields(self, src: str, fields: dict):
        if not fields:
            return
        with self._lock:
            item = self._active.get(src)
            if item:
                item.update(fields)

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
            self._rename.pop(src, None)
            self._confirm_required.discard(src)
            self._confirm_ok.discard(src)
            now = time.time()
            record = {
                "source": src,
                "destination": dest,
                "state": "success" if success else "error",
                "finished_at": now,
                "started_at": start.get("started_at") if start else None,
                "message": message,
                "info": start.get("info") if start else None,
                "eta_sec": self._etas.pop(src, None),
                "progress": 100.0 if success else start.get("progress") if start else None,
            }
            if self._history:
                last = self._history[-1]
                same = (
                    last.get("source") == record["source"]
                    and last.get("destination") == record["destination"]
                    and last.get("state") == record["state"]
                    and last.get("message") == record["message"]
                    and abs(last.get("finished_at", 0) - now) < 2
                )
                if same:
                    return
            self._history.append(record)
            if len(self._history) > self._history_size:
                self._history = self._history[-self._history_size :]

    def update_progress(self, src: str, progress: float):
        with self._lock:
            item = self._active.get(src)
            if item:
                pct = max(0.0, min(100.0, progress))
                item["progress"] = pct
                started_at = item.get("started_at")
                if started_at and pct > 0:
                    try:
                        elapsed = time.time() - started_at
                        eta = (elapsed * (100.0 - pct) / pct)
                        self._etas[src] = max(0.0, eta)
                    except Exception:
                        pass

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
                        "rename_to": self._rename.get(key),
                    }
                )
            history = list(self._history)
            disc_info = self._disc_info
            disc_pending = self._disc_pending
            disc_rip_blocked = self._disc_rip_blocked
            disc_rip_requested = self._disc_rip_requested
            disc_scan_paused = self._disc_scan_paused
            disc_scan_inflight = self._disc_scan_inflight
            disc_present = self._disc_present
            # If a disc rip is active, force disc_pending so UI shows presence
            if not disc_pending:
                disc_pending = any(
                    (a.get("source", "") or "").startswith("disc:") or a.get("state") == "ripping"
                    for a in active
                )
            usb_status = dict(self._usb_status)
            info_payload = (disc_info.get("info") if isinstance(disc_info, dict) else disc_info) or {}
            titles_count = len(info_payload.get("titles") or [])
            if disc_present is not False and titles_count == 0 and self._disc_info_cache:
                cache_key = self._disc_info_cache_key
                if not cache_key or not self._disc_key or cache_key == self._disc_key:
                    cache_payload = (
                        self._disc_info_cache.get("info")
                        if isinstance(self._disc_info_cache, dict)
                        else self._disc_info_cache
                    ) or {}
                    cache_titles = len(cache_payload.get("titles") or [])
                    if cache_titles:
                        disc_info = self._disc_info_cache
                        info_payload = cache_payload
                        titles_count = cache_titles
            summary = info_payload.get("summary") or {}
            label = summary.get("disc_label") or summary.get("label") or ""
            disc_timing = {
                "disc_inserted_at": self._disc_inserted_ts,
                "disc_removed_at": self._disc_removed_ts,
                "disc_info_first_at": self._disc_info_first_ts,
                "disc_titles_first_at": self._disc_titles_first_ts,
                "disc_info_last_at": self._disc_info_last_ts,
                "disc_titles_last_at": self._disc_titles_last_ts,
                "disc_info_cleared_at": self._disc_info_cleared_ts,
                "disc_titles_cleared_at": self._disc_titles_cleared_ts,
                "disc_label_first_at": self._disc_label_first_ts,
                "disc_label_last_at": self._disc_label_last_ts,
                "disc_label_cleared_at": self._disc_label_cleared_ts,
                "disc_scan_started_at": self._disc_scan_started_ts,
                "disc_scan_last_at": self._disc_scan_last_ts,
                "disc_scan_last_duration_sec": self._disc_scan_last_duration,
                "disc_scan_last_timed_out": self._disc_scan_last_timed_out,
            }
            if self._disc_info_last_ts:
                disc_timing["disc_info_age_sec"] = max(0.0, now - self._disc_info_last_ts)
            if self._disc_titles_last_ts:
                disc_timing["disc_titles_age_sec"] = max(0.0, now - self._disc_titles_last_ts)
            if self._disc_label_last_ts:
                disc_timing["disc_label_age_sec"] = max(0.0, now - self._disc_label_last_ts)
            if self._disc_inserted_ts and self._disc_info_first_ts:
                disc_timing["disc_info_time_to_first_sec"] = max(0.0, self._disc_info_first_ts - self._disc_inserted_ts)
            if self._disc_inserted_ts and self._disc_titles_first_ts:
                disc_timing["disc_titles_time_to_first_sec"] = max(0.0, self._disc_titles_first_ts - self._disc_inserted_ts)
            if self._disc_inserted_ts and self._disc_label_first_ts:
                disc_timing["disc_label_time_to_first_sec"] = max(0.0, self._disc_label_first_ts - self._disc_inserted_ts)
            if self._disc_titles_first_ts and self._disc_titles_last_ts:
                disc_timing["disc_titles_visible_for_sec"] = max(0.0, self._disc_titles_last_ts - self._disc_titles_first_ts)
            if disc_present and titles_count == 0 and self._disc_titles_last_ts:
                disc_timing["disc_titles_missing_for_sec"] = max(0.0, now - self._disc_titles_last_ts)
            if disc_present and not info_payload and self._disc_info_last_ts:
                disc_timing["disc_info_missing_for_sec"] = max(0.0, now - self._disc_info_last_ts)
            if disc_present and not label and self._disc_label_last_ts:
                disc_timing["disc_label_missing_for_sec"] = max(0.0, now - self._disc_label_last_ts)
        return {
            "active": active,
            "recent": history[::-1],  # newest first
            "timestamp": now,
            "disc_info": disc_info,
            "disc_pending": disc_pending,
            "disc_rip_blocked": disc_rip_blocked,
            "disc_rip_requested": disc_rip_requested,
            "disc_scan_paused": disc_scan_paused,
            "disc_scan_inflight": disc_scan_inflight,
            "disc_present": disc_present,
            "disc_titles_count": titles_count,
            "disc_timing": disc_timing,
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
    def set_disc_info(self, info: dict, force: bool = False):
        now = time.time()
        with self._lock:
            if self._disc_preserve_info and self._disc_info and not force:
                return
            payload = (info.get("info") if isinstance(info, dict) else info) or {}
            incoming_titles = payload.get("titles") or []
            incoming_pending = bool(payload.get("scan_pending"))
            if self._disc_info and not force:
                existing_payload = (self._disc_info.get("info") if isinstance(self._disc_info, dict) else self._disc_info) or {}
                existing_titles = existing_payload.get("titles") or []
                if existing_titles and not incoming_titles:
                    self._disc_pending = bool(incoming_pending and not existing_titles)
                    return
            self._disc_info = info
            self._disc_pending = bool(not incoming_titles)
            self._disc_info_last_ts = now
            self._disc_info_cleared_ts = None
            if self._disc_present and self._disc_info_first_ts is None:
                self._disc_info_first_ts = now
            if self._disc_key is None and isinstance(info, dict):
                disc_index = info.get("disc_index")
                summary = payload.get("summary") or {}
                label = summary.get("disc_label") or summary.get("label") or ""
                drive = summary.get("drive") or ""
                if label or drive:
                    self._disc_key = f"{label}|{drive}"
                elif disc_index is not None:
                    self._disc_key = f"disc:{disc_index}"
            if incoming_titles:
                self._disc_titles_last_ts = now
                self._disc_titles_cleared_ts = None
                if self._disc_present and self._disc_titles_first_ts is None:
                    self._disc_titles_first_ts = now
                cache_key = self._disc_key
                if not cache_key and isinstance(info, dict):
                    disc_index = info.get("disc_index")
                    if disc_index is not None:
                        cache_key = f"disc:{disc_index}"
                self._disc_info_cache = info
                self._disc_info_cache_key = cache_key
            summary = payload.get("summary") or {}
            label = summary.get("disc_label") or summary.get("label") or ""
            if label:
                self._disc_label_last_ts = now
                self._disc_label_cleared_ts = None
                if self._disc_present and self._disc_label_first_ts is None:
                    self._disc_label_first_ts = now

    def clear_disc_info(self):
        now = time.time()
        with self._lock:
            if self._disc_present:
                self._disc_info_cleared_ts = now
                if self._disc_titles_last_ts and self._disc_titles_cleared_ts is None:
                    self._disc_titles_cleared_ts = now
                if self._disc_label_last_ts and self._disc_label_cleared_ts is None:
                    self._disc_label_cleared_ts = now
            self._disc_info = None
            self._disc_pending = False
            self._disc_rip_requested = False
            self._disc_rip_mode = None
            self._disc_auto_queue = []
            self._disc_auto_key = None
            self._disc_auto_complete_key = None
            self._disc_preserve_info = False
            if self._disc_present is False:
                self._disc_key = None

    def disc_info(self):
        with self._lock:
            info = self._disc_info
            if self._disc_present is False:
                return info
            payload = (info.get("info") if isinstance(info, dict) else info) or {}
            titles = payload.get("titles") or []
            if titles:
                return info
            cache = self._disc_info_cache
            if cache:
                cache_payload = (cache.get("info") if isinstance(cache, dict) else cache) or {}
                cache_titles = cache_payload.get("titles") or []
                cache_key = self._disc_info_cache_key
                if cache_titles and (not cache_key or not self._disc_key or cache_key == self._disc_key):
                    return cache
            return info

    def disc_pending(self) -> bool:
        with self._lock:
            return self._disc_pending

    def set_disc_pending(self, value: bool):
        with self._lock:
            self._disc_pending = bool(value)

    def request_disc_rip(self, mode: str = "manual"):
        with self._lock:
            if mode == "auto" and self._disc_rip_blocked:
                return
            if mode == "auto" and self._disc_rip_requested and self._disc_rip_mode == "manual":
                return
            self._disc_rip_requested = True
            self._disc_rip_mode = mode
            self._disc_pending = True
            if mode == "manual":
                self._disc_rip_blocked = False
                self._disc_scan_paused = False
            if mode == "manual":
                self._disc_preserve_info = True

    def consume_disc_rip_request(self):
        with self._lock:
            req = self._disc_rip_requested
            self._disc_rip_requested = False
            mode = self._disc_rip_mode
            self._disc_rip_mode = None
            return mode if req else None

    def disc_rip_requested(self) -> bool:
        with self._lock:
            return bool(self._disc_rip_requested)

    def set_disc_preserve(self, value: bool):
        with self._lock:
            self._disc_preserve_info = bool(value)

    def disc_rip_requested(self) -> bool:
        with self._lock:
            return self._disc_rip_requested

    def set_disc_auto_queue(self, key: str, titles: list):
        with self._lock:
            self._disc_auto_key = key
            self._disc_auto_queue = list(titles or [])

    def disc_auto_queue(self):
        with self._lock:
            return list(self._disc_auto_queue)

    def disc_auto_key(self):
        with self._lock:
            return self._disc_auto_key

    def clear_disc_auto_queue(self):
        with self._lock:
            self._disc_auto_queue = []
            self._disc_auto_key = None

    def set_disc_auto_complete(self, key: str):
        with self._lock:
            self._disc_auto_complete_key = key

    def clear_disc_auto_complete(self):
        with self._lock:
            self._disc_auto_complete_key = None

    def disc_auto_complete(self, key: str) -> bool:
        with self._lock:
            return bool(self._disc_auto_complete_key and key and self._disc_auto_complete_key == key)

    def pop_disc_auto_title(self):
        with self._lock:
            if not self._disc_auto_queue:
                return None
            return self._disc_auto_queue.pop(0)

    def block_disc_rip(self):
        with self._lock:
            self._disc_rip_blocked = True
            self._disc_rip_requested = False

    def allow_disc_rip(self):
        with self._lock:
            self._disc_rip_blocked = False

    def disc_rip_blocked(self) -> bool:
        with self._lock:
            return self._disc_rip_blocked

    def set_disc_present(self, present: bool):
        now = time.time()
        with self._lock:
            prev = self._disc_present
            self._disc_present = bool(present)
            if present and prev is not True:
                self._disc_inserted_ts = now
                self._disc_key = None
                self._disc_info_cache = None
                self._disc_info_cache_key = None
                self._disc_info_first_ts = None
                self._disc_titles_first_ts = None
                self._disc_info_last_ts = None
                self._disc_titles_last_ts = None
                self._disc_info_cleared_ts = None
                self._disc_titles_cleared_ts = None
                self._disc_label_first_ts = None
                self._disc_label_last_ts = None
                self._disc_label_cleared_ts = None
            if not present and prev is not False:
                self._disc_removed_ts = now
                self._disc_key = None
                self._disc_info_cache = None
                self._disc_info_cache_key = None
                self._disc_rip_requested = False
                self._disc_rip_mode = None
                self._disc_pending = False
                self._disc_auto_queue = []
                self._disc_auto_key = None
                self._disc_auto_complete_key = None
                self._disc_preserve_info = False

    def set_disc_key(self, key: str, force: bool = False):
        if not key:
            return
        with self._lock:
            if force or not self._disc_key:
                self._disc_key = key

    def disc_key(self):
        with self._lock:
            return self._disc_key

    def disc_present(self):
        with self._lock:
            return self._disc_present

    def pause_disc_scan(self):
        with self._lock:
            self._disc_scan_paused = True

    def resume_disc_scan(self):
        with self._lock:
            self._disc_scan_paused = False

    def disc_scan_paused(self) -> bool:
        with self._lock:
            return self._disc_scan_paused

    def can_start_disc_scan(self, force: bool = False) -> bool:
        now = time.time()
        with self._lock:
            if self._disc_scan_inflight:
                return False
            if force:
                return True
            if self._disc_scan_paused or self._disc_rip_blocked:
                return False
            return now >= self._disc_scan_cooldown_until

    def start_disc_scan(self) -> bool:
        with self._lock:
            if self._disc_scan_inflight:
                return False
            self._disc_scan_inflight = True
            self._disc_scan_started_ts = time.time()
            return True

    def finish_disc_scan(self, success: bool, timed_out: bool = False):
        now = time.time()
        with self._lock:
            self._disc_scan_inflight = False
            self._disc_scan_last_ts = now
            if self._disc_scan_started_ts:
                self._disc_scan_last_duration = max(0.0, now - self._disc_scan_started_ts)
            self._disc_scan_last_timed_out = bool(timed_out)
            if success and not timed_out:
                self._disc_scan_failures = 0
                return
            self._disc_scan_failures += 1
            backoff = min(300, 60 * self._disc_scan_failures)
            self._disc_scan_cooldown_until = max(self._disc_scan_cooldown_until, now + backoff)

    def set_disc_scan_cooldown(self, seconds: int):
        now = time.time()
        with self._lock:
            self._disc_scan_cooldown_until = max(self._disc_scan_cooldown_until, now + max(0, int(seconds)))

    def disc_scan_inflight(self) -> bool:
        with self._lock:
            return self._disc_scan_inflight
