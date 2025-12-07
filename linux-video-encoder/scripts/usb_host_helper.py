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


def find_first_usb_partition(lsblk_text: str, target: str):
    """
    Find the first partition that is removable or has usb transport.
    Returns tuple (device, fstype) or (None, None).
    """
    disk_transport: Dict[str, str] = {}
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
        if not (rm == "1" or tran.lower() == "usb"):
            continue
        dev = f"/dev/{name}"
        if mp == target:
            return dev, fs
        return dev, fs
    return None, None


def ensure_shared(mountpoint: str):
    os.makedirs(mountpoint, exist_ok=True)
    subprocess.run(["mount", "--make-rshared", mountpoint], check=False)


def attempt_mount(dev: str, fstype: str, mountpoint: str) -> Dict[str, str]:
    ensure_shared(mountpoint)
    subprocess.run(["umount", mountpoint], check=False)
    opts = "uid=1000,gid=1000,fmask=0022,dmask=0022,iocharset=utf8"
    cmd = ["mount", "-o", opts]
    if fstype:
        cmd += ["-t", fstype]
    cmd += [dev, mountpoint]
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if res.returncode != 0:
        # retry without explicit fstype
        res = subprocess.run(["mount", "-o", opts, dev, mountpoint], capture_output=True, text=True, check=False)
    if res.returncode == 0:
        return {"ok": True, "device": dev, "fstype": fstype or "auto", "mountpoint": mountpoint}
    msg = res.stderr.strip() or res.stdout.strip() or "mount failed"
    return {"ok": False, "device": dev, "error": msg}


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
                dev = fstype = None
                lsblk_text = ""
                for i in range(3):
                    lsblk_text = run_lsblk(pretty=True)
                    dev, fstype = find_first_usb_partition(lsblk_text, self.helper_mountpoint)
                    attempts.append({"attempt": i + 1, "lsblk": lsblk_text.strip()})
                    if dev:
                        break
                    rescan_block_devices()
                if not dev:
                    self._json(200, {"ok": False, "error": "no removable/usb partition after rescans", "attempts": attempts})
                    return
                result = attempt_mount(dev, fstype, self.helper_mountpoint)
                result["attempts"] = attempts
                self._json(200 if result.get("ok") else 500, result)
                return
            except Exception as e:
                logging.exception("refresh failed")
                self._json(500, {"ok": False, "error": str(e)})
                return
        self._json(404, {"error": "not found"})


def main():
    parser = argparse.ArgumentParser(description="Host USB helper for linux-video-encoder.")
    parser.add_argument("--listen", default="127.0.0.1", help="Listen address")
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
