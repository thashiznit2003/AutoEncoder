#!/usr/bin/env python3
"""
Host-side helper to manage USB mounts for linux-video-encoder.

Runs a tiny HTTP server (default 127.0.0.1:8765) with:
  POST /usb/refresh   -> attempt to mount the first removable/USB partition to the target mountpoint
  GET  /usb/status    -> report lsblk inventory and current mount state

Intended to be installed as a systemd service on the host. The container can
reach it via host.docker.internal (add host-gateway in compose) or via a mapped port.
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Dict, List
import shutil


def run_lsblk(pretty: bool = True) -> str:
    """
    Return lsblk output. Uses key/value (-P) when pretty=True, otherwise space-delimited.
    """
    flags = ["-nP"] if pretty else ["-nr"]
    try:
        res = subprocess.run(
            ["lsblk", *flags, "-o", "NAME,TYPE,RM,MOUNTPOINT,FSTYPE,TRAN"],
            capture_output=True,
            text=True,
            check=False,
        )
        out = res.stdout
        if not out.strip():
            # retry non-pretty if empty
            if pretty:
                return run_lsblk(pretty=False)
            return res.stdout or res.stderr or ""
        return out
    except Exception as e:
        return f"lsblk failed: {e}"


def parse_lsblk_lines(lines: List[str]) -> List[Dict[str, str]]:
    entries = []
    for line in lines:
        parsed: Dict[str, str] = {}
        for token in line.split():
            if "=" in token:
                k, v = token.split("=", 1)
                parsed[k] = v.strip('"')
        if parsed:
            entries.append(parsed)
    return entries


def list_usb_partitions(lsblk_text: str, target: str) -> List[Dict[str, str]]:
    """
    List candidate partitions that are removable or have usb transport,
    skipping system mounts. Returns list of dicts with keys: device, fstype, mountpoint.
    """
    skip_mounts = {"/", "/boot", "/boot/efi"}
    disk_transport: Dict[str, str] = {}
    candidates: List[Dict[str, str]] = []
    for line in lsblk_text.splitlines():
        entry = {}
        # try key/value first
        if "NAME=" in line:
            for token in line.split():
                if "=" in token:
                    k, v = token.split("=", 1)
                    entry[k] = v.strip('"')
        else:
            parts = line.split()
            if len(parts) >= 3:
                entry = {
                    "NAME": parts[0],
                    "TYPE": parts[1],
                    "RM": parts[2],
                    "MOUNTPOINT": parts[3] if len(parts) >= 4 else "",
                    "FSTYPE": parts[4] if len(parts) >= 5 else "",
                    "TRAN": parts[5] if len(parts) >= 6 else "",
                }
        name = entry.get("NAME", "")
        typ = entry.get("TYPE", "")
        rm = entry.get("RM", "")
        mp = entry.get("MOUNTPOINT", "") or ""
        fs = entry.get("FSTYPE", "") or ""
        tran = entry.get("TRAN", "") or ""
        if not name or not typ:
            continue
        if typ == "disk":
            disk_transport[name] = tran
            continue
        if typ != "part":
            continue
        if not tran:
            for disk_name, disk_tran in disk_transport.items():
                if name.startswith(disk_name):
                    tran = disk_tran
                    break
        # skip partitions already mounted elsewhere (e.g., root/boot) unless it's the target
        if mp in skip_mounts:
            continue
        if mp and mp != target:
            continue
        if not (rm == "1" or tran.lower() == "usb"):
            continue
        candidates.append({"device": f"/dev/{name}", "fstype": fs or None, "mountpoint": mp})
    return candidates


def ensure_shared(mountpoint: str):
    os.makedirs(mountpoint, exist_ok=True)
    # bind to self and set shared to ensure propagation into rslave bind mounts
    subprocess.run(["mount", "--bind", mountpoint, mountpoint], check=False)
    subprocess.run(["mount", "--make-rshared", mountpoint], check=False)


def find_first_usb_partition(lsblk_text: str, target: str):
    """
    Return the first candidate partition tuple (device, fstype) or (None, None).
    """
    candidates = list_usb_partitions(lsblk_text, target)
    if not candidates:
        return None, None
    first = candidates[0]
    return first.get("device"), first.get("fstype")


def attempt_mount(dev: str, fstype: str, mountpoint: str) -> Dict[str, str]:
    ensure_shared(mountpoint)
    # Always try to unmount first to clean up stale/broken mounts (both the target and the common /mnt/usb)
    for mp in {mountpoint, "/mnt/usb"}:
        subprocess.run(["umount", mp], check=False)
    opts = "uid=1000,gid=1000,fmask=0022,dmask=0022,iocharset=utf8"

    def do_mount(force_fs: bool) -> subprocess.CompletedProcess:
        cmd = ["mount", "-o", opts]
        if force_fs and fstype:
            cmd += ["-t", fstype]
        cmd += [dev, mountpoint]
        return subprocess.run(cmd, capture_output=True, text=True, check=False)

    def run_fsck_once():
        if fstype and fstype.lower() != "exfat":
            return False, "fsck skipped (fstype != exfat)"
        if not shutil.which("fsck.exfat"):
            return False, "fsck.exfat not installed"
        res_fsck = subprocess.run(["fsck.exfat", "-a", dev], capture_output=True, text=True, check=False)
        ok = res_fsck.returncode == 0
        msg = res_fsck.stderr.strip() or res_fsck.stdout.strip() or str(res_fsck.returncode)
        return ok, msg

    res = do_mount(True)
    fsck_msg = None
    fsck_ran = False
    if res.returncode != 0:
        # retry without explicit fs type
        res = do_mount(False)
    if res.returncode != 0:
        fsck_ok, fsck_msg = run_fsck_once()
        fsck_ran = fsck_ok or fsck_msg is not None
        # final retry after rescan/unmount in case of stale state
        subprocess.run(["umount", mountpoint], check=False)
        rescan_block_devices()
        res = do_mount(False)

    result: Dict[str, str] = {"device": dev, "fstype": fstype or "auto", "mountpoint": mountpoint}
    if res.returncode == 0:
        # validate readability; if EIO, try fsck+retry once
        try:
            os.listdir(mountpoint)
        except OSError as e:
            result["warn"] = f"read error after mount: {e}"
            fsck_ok, fsck_msg = run_fsck_once()
            fsck_ran = fsck_ran or fsck_ok or (fsck_msg is not None)
            subprocess.run(["umount", mountpoint], check=False)
            res = do_mount(False)
            if res.returncode == 0:
                try:
                    os.listdir(mountpoint)
                except Exception as e2:
                    result["error"] = f"read error after fsck/mount: {e2}"
                    result["ok"] = False
                    if fsck_msg:
                        result["fsck_msg"] = fsck_msg
                    return result
            else:
                result["error"] = res.stderr.strip() or res.stdout.strip() or "mount failed after fsck"
                result["ok"] = False
                if fsck_msg:
                    result["fsck_msg"] = fsck_msg
                return result
        result["ok"] = True
        if fsck_ran:
            result["fsck_msg"] = fsck_msg
        return result
    msg = res.stderr.strip() or res.stdout.strip() or "mount failed"
    result["ok"] = False
    result["error"] = msg
    if fsck_ran and fsck_msg:
        result["fsck_msg"] = fsck_msg
    return result


def rescan_block_devices():
    """Ask udev/kernel to rescan block devices to catch late-arriving sticks."""
    subprocess.run(["udevadm", "trigger", "--action=change", "--subsystem-match=block"], check=False)
    subprocess.run(["partprobe"], check=False)
    time.sleep(1.0)


class Handler(BaseHTTPRequestHandler):
    helper_mountpoint: str = "/linux-video-encoder/AutoEncoder/linux-video-encoder/USB"

    def _json(self, code: int, payload: Dict):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        logging.info("%s - %s", self.client_address[0], fmt % args)

    def do_GET(self):
        if self.path.startswith("/usb/status"):
            lsblk_text = run_lsblk(pretty=True)
            dev, fstype = find_first_usb_partition(lsblk_text, self.helper_mountpoint)
            payload = {
                "lsblk": lsblk_text,
                "candidate": dev,
                "fstype": fstype,
                "mountpoint": self.helper_mountpoint,
            }
            self._json(200, payload)
            return
        self._json(404, {"error": "not found"})

    def do_POST(self):
        if self.path.startswith("/usb/eject"):
            try:
                target = self.helper_mountpoint
                length = int(self.headers.get("Content-Length", "0") or 0)
                if length:
                    body = self.rfile.read(length)
                    try:
                        data = json.loads(body.decode("utf-8"))
                        target = data.get("target") or target
                    except Exception:
                        pass
                # attempt unmount on both the target and /mnt/usb to clear stale mounts
                attempts = []
                for mp in {target, "/mnt/usb"}:
                    res = subprocess.run(["umount", mp], capture_output=True, text=True, check=False)
                    attempts.append({"mountpoint": mp, "returncode": res.returncode, "stderr": res.stderr.strip(), "stdout": res.stdout.strip()})
                rescan_block_devices()
                return self._json(200, {"ok": True, "attempts": attempts, "mountpoint": target})
            except Exception as e:
                logging.exception("eject failed")
                return self._json(200, {"ok": False, "error": str(e)})

        if self.path.startswith("/usb/force_remount"):
            try:
                length = int(self.headers.get("Content-Length", "0") or 0)
                target = self.helper_mountpoint
                attempts = 5
                delay = 2.0
                if length:
                    body = self.rfile.read(length)
                    try:
                        data = json.loads(body.decode("utf-8"))
                        target = data.get("target") or target
                        attempts = int(data.get("attempts", attempts))
                        delay = float(data.get("delay", delay))
                    except Exception:
                        pass
                results = []
                last_err = None
                for i in range(attempts):
                    subprocess.run(["umount", target], check=False)
                    rescan_block_devices()
                    lsblk_text = run_lsblk(pretty=True)
                    parts = list_usb_partitions(lsblk_text, target)
                    step = {"attempt": i + 1, "lsblk": lsblk_text.strip(), "candidates": parts}
                    if not parts:
                        step["ok"] = False
                        step["error"] = "no removable/usb partition"
                        results.append(step)
                        last_err = step.get("error")
                        time.sleep(delay)
                        continue
                    mounted_this_attempt = False
                    for cand in parts:
                        dev = cand.get("device")
                        fstype = cand.get("fstype")
                        if not dev:
                            continue
                        mount_res = attempt_mount(dev, fstype, target)
                        sub = {"device": dev, "fstype": fstype, "mount_result": mount_res}
                        try:
                            entries = [e.name for e in os.scandir(target)]
                            sub["entries"] = entries[:20]
                            if any(name not in (".", "..") for name in entries):
                                results.append({**step, **sub, "ok": True})
                                return self._json(200, {"ok": True, "device": dev, "fstype": fstype or "auto", "attempts": results})
                        except Exception as e:
                            sub["entries_error"] = str(e)
                        results.append({**step, **sub, "ok": mount_res.get("ok", False), "error": mount_res.get("error")})
                        last_err = mount_res.get("error")
                        mounted_this_attempt = mounted_this_attempt or mount_res.get("ok", False)
                    if not mounted_this_attempt:
                        time.sleep(delay)
                return self._json(200, {"ok": False, "error": last_err or "force remount failed", "attempts": results})
            except Exception as e:
                logging.exception("force remount failed")
                self._json(200, {"ok": False, "error": str(e), "attempts": results if 'results' in locals() else []})
                return

        if self.path.startswith("/usb/refresh"):
            try:
                length = int(self.headers.get("Content-Length", "0") or 0)
                if length:
                    body = self.rfile.read(length)
                    try:
                        data = json.loads(body.decode("utf-8"))
                        mp = data.get("target")
                        if mp:
                            self.helper_mountpoint = mp
                    except Exception:
                        pass
                attempts = []
                lsblk_text = ""
                last_err = None
                for i in range(3):
                    lsblk_text = run_lsblk(pretty=True)
                    parts = list_usb_partitions(lsblk_text, self.helper_mountpoint)
                    attempts.append({"attempt": i + 1, "lsblk": lsblk_text.strip(), "candidates": parts})
                    if not parts:
                        rescan_block_devices()
                        continue
                    for cand in parts:
                        dev = cand.get("device")
                        fstype = cand.get("fstype")
                        if not dev:
                            continue
                        mount_res = attempt_mount(dev, fstype, self.helper_mountpoint)
                        step = {"device": dev, "fstype": fstype, "mount_result": mount_res}
                        try:
                            entries = [e.name for e in os.scandir(self.helper_mountpoint)]
                            step["entries"] = entries[:20]
                            if any(name not in (".", "..") for name in entries):
                                self._json(200, {"ok": True, "device": dev, "fstype": fstype or "auto", "attempts": attempts + [step]})
                                return
                        except Exception as e:
                            step["entries_error"] = str(e)
                        attempts.append(step)
                        last_err = mount_res.get("error") if isinstance(mount_res, dict) else None
                    rescan_block_devices()
                self._json(200, {"ok": False, "error": last_err or "no removable/usb partition after rescans", "attempts": attempts})
                return
            except Exception as e:
                logging.exception("refresh failed")
                self._json(500, {"ok": False, "error": str(e)})
                return
        self._json(404, {"error": "not found"})


def main():
    parser = argparse.ArgumentParser(description="Host USB helper for linux-video-encoder.")
    parser.add_argument("--listen", default="0.0.0.0", help="Listen address (use 0.0.0.0 so containers can reach it)")
    parser.add_argument("--port", type=int, default=8765, help="Listen port")
    parser.add_argument("--mountpoint", default="/linux-video-encoder/AutoEncoder/linux-video-encoder/USB", help="Mountpoint to use")
    args = parser.parse_args()

    Handler.helper_mountpoint = args.mountpoint
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
    server = HTTPServer((args.listen, args.port), Handler)
    logging.info("usb_host_helper listening on %s:%s targeting mountpoint %s", args.listen, args.port, args.mountpoint)
    server.serve_forever()


if __name__ == "__main__":
    if os.geteuid() != 0:
        print("This helper must run as root to mount/umount.", file=sys.stderr)
        sys.exit(1)
    main()
