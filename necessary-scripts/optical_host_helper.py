#!/usr/bin/env python3
"""
Host-side helper to manage optical drive visibility.

Endpoints:
  GET  /optical/status   -> returns detected optical devices and selected dev paths
  POST /optical/refresh  -> rescans SCSI hosts and returns updated status
  POST /optical/reset    -> attempts a soft reset on the selected drive
  POST /optical/eject    -> opens the tray on the selected drive
  POST /optical/close    -> closes the tray on the selected drive
"""

import argparse
import json
import logging
import os
import subprocess
import time
from http.server import BaseHTTPRequestHandler, HTTPServer


def run(cmd, timeout: float | None = None):
    return subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=timeout)


def rescan_scsi_hosts():
    for host in os.listdir("/sys/class/scsi_host"):
        scan = f"/sys/class/scsi_host/{host}/scan"
        try:
            with open(scan, "w", encoding="utf-8") as f:
                f.write("- - -")
        except Exception:
            continue
    run(["udevadm", "trigger", "--action=change", "--subsystem-match=block"])
    time.sleep(1.0)


def scsi_generic_for_sr(sr: str):
    # /sys/class/block/sr0/device/scsi_generic/sg1
    path = f"/sys/class/block/{sr}/device/scsi_generic"
    try:
        entries = os.listdir(path)
        if entries:
            return f"/dev/{entries[0]}"
    except Exception:
        pass
    return None


def _read_sys(path: str) -> str | None:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return None


def disc_present_for_sr(sr: str) -> bool:
    device_dir = f"/sys/class/block/{sr}/device"
    medium_state = (_read_sys(f"{device_dir}/medium_state") or "").lower()
    if medium_state:
        if "empty" in medium_state or "no" in medium_state:
            return False
        if "present" in medium_state:
            return True
    state = (_read_sys(f"{device_dir}/state") or "").lower()
    if state:
        if "not ready" in state or "offline" in state or "no medium" in state:
            return False
    sg = scsi_generic_for_sr(sr)
    if sg and os.path.exists(sg) and run(["which", "sg_turs"]).returncode == 0:
        try:
            res = run(["sg_turs", "--quiet", sg], timeout=2)
            return res.returncode == 0
        except Exception:
            pass
    media = _read_sys(f"{device_dir}/media")
    if media in {"0", "1"}:
        return media == "1"
    size = _read_sys(f"/sys/class/block/{sr}/size")
    if size and size.isdigit():
        return int(size) > 0
    return False


def udev_props(devnode: str):
    res = run(["udevadm", "info", "--query=property", "--name", devnode])
    props = {}
    for line in (res.stdout or "").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            props[k] = v
    return props


def detect_optical_devices():
    res = run(["lsblk", "-nP", "-o", "NAME,TYPE,RM,TRAN,MODEL,RO"])
    devices = []
    for line in (res.stdout or "").splitlines():
        if "TYPE=" not in line:
            continue
        parts = {}
        for token in line.split():
            if "=" in token:
                k, v = token.split("=", 1)
                parts[k] = v.strip('"')
        if parts.get("TYPE") != "rom":
            continue
        name = parts.get("NAME")
        if not name:
            continue
        sr = f"/dev/{name}"
        props = udev_props(sr)
        present = disc_present_for_sr(name)
        devices.append(
            {
                "sr_device": sr,
                "sg_device": scsi_generic_for_sr(name),
                "model": props.get("ID_MODEL") or parts.get("MODEL"),
                "serial": props.get("ID_SERIAL_SHORT") or props.get("ID_SERIAL"),
                "bus": props.get("ID_BUS") or parts.get("TRAN"),
                "label": props.get("ID_FS_LABEL"),
                "present": present,
            }
        )
    return devices


def build_status():
    devices = detect_optical_devices()
    selected = devices[0] if devices else None
    return {"devices": devices, "selected": selected}


def reset_optical_device(selected: dict) -> dict:
    if not selected:
        return {"ok": False, "error": "no optical device detected"}
    sr_device = selected.get("sr_device")
    sg_device = selected.get("sg_device")
    actions = []
    errors = []
    ok = False
    if sg_device and os.path.exists(sg_device) and run(["which", "sg_reset"]).returncode == 0:
        res = run(["sg_reset", "--device", sg_device])
        actions.append({"cmd": "sg_reset --device", "rc": res.returncode})
        if res.returncode == 0:
            ok = True
        else:
            errors.append(res.stderr.strip() or res.stdout.strip() or "sg_reset failed")
    rescan_scsi_hosts()
    actions.append({"cmd": "scsi rescan", "rc": 0})
    ok = ok or not errors
    payload = {"ok": ok, "actions": actions}
    if errors:
        payload["errors"] = errors
    return payload


def eject_optical_device(selected: dict, close: bool = False) -> dict:
    if not selected:
        return {"ok": False, "error": "no optical device detected"}
    sr_device = selected.get("sr_device")
    actions = []
    errors = []
    ok = False
    if sr_device and os.path.exists(sr_device) and run(["which", "eject"]).returncode == 0:
        cmd = ["eject", "-t", sr_device] if close else ["eject", sr_device]
        res = run(cmd)
        actions.append({"cmd": " ".join(cmd), "rc": res.returncode})
        if res.returncode == 0:
            ok = True
        else:
            errors.append(res.stderr.strip() or res.stdout.strip() or "eject failed")
    payload = {"ok": ok or not errors, "actions": actions}
    if errors:
        payload["errors"] = errors
    return payload


class Handler(BaseHTTPRequestHandler):
    def _json(self, code: int, payload: dict):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        logging.info("%s - %s", self.client_address[0], fmt % args)

    def do_GET(self):
        if self.path.startswith("/optical/status"):
            self._json(200, build_status())
            return
        self._json(404, {"error": "not found"})

    def do_POST(self):
        if self.path.startswith("/optical/refresh"):
            rescan_scsi_hosts()
            self._json(200, build_status())
            return
        if self.path.startswith("/optical/reset"):
            status = build_status()
            result = reset_optical_device(status.get("selected") or {})
            self._json(200 if result.get("ok") else 500, result)
            return
        if self.path.startswith("/optical/eject"):
            status = build_status()
            result = eject_optical_device(status.get("selected") or {}, close=False)
            self._json(200 if result.get("ok") else 500, result)
            return
        if self.path.startswith("/optical/close"):
            status = build_status()
            result = eject_optical_device(status.get("selected") or {}, close=True)
            self._json(200 if result.get("ok") else 500, result)
            return
        self._json(404, {"error": "not found"})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--listen", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8767)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
    server = HTTPServer((args.listen, args.port), Handler)
    logging.info("Optical helper listening on %s:%s", args.listen, args.port)
    server.serve_forever()


if __name__ == "__main__":
    main()
