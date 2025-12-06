#!/usr/bin/env python3
"""
Helper to mount an SMB share with input validation and credential file handling.
Intended to be called by the app instead of invoking mount directly.
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse

STATE_DIR = Path("/var/lib/autoencoder/state")
UNSAFE_CHARS = set(";|&<>`$()")


def sanitize_component(val: str) -> str:
    if any(ord(c) < 32 for c in val):
        raise ValueError("control characters not allowed")
    if any(c in UNSAFE_CHARS for c in val):
        raise ValueError("disallowed characters present")
    return val


def normalize_smb_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in ("smb", ""):
        raise ValueError("scheme must be smb://")
    if not parsed.netloc:
        raise ValueError("missing server/share")
    sanitize_component(parsed.netloc)
    path = (parsed.path or "").lstrip("/")
    # Normalize path, rejecting traversal
    norm_path = PurePosixPath("/" + path)
    if ".." in norm_path.parts:
        raise ValueError("path traversal not allowed")
    # Allow spaces; reject unsafe chars
    sanitize_component(path.replace("/", ""))
    norm_str = "" if str(norm_path) == "/" else str(norm_path)
    return "//" + parsed.netloc + norm_str


def build_credentials_file(username: str, password: str, domain: str | None) -> Path | None:
    if not username and not password:
        return None
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    cred_path = STATE_DIR / "smb_credentials"
    lines = []
    lines.append(f"username={username}")
    lines.append(f"password={password}")
    if domain:
        lines.append(f"domain={domain}")
    cred_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.chmod(cred_path, 0o600)
    return cred_path


def run_mount(unc: str, mountpoint: Path, username: str, password: str, domain: str | None, vers: str | None) -> tuple[int, str]:
    mountpoint.mkdir(parents=True, exist_ok=True)
    cred_file = None
    try:
        cred_file = build_credentials_file(username, password, domain)
        base_opts = ["rw", "iocharset=utf8"]
        if cred_file:
            base_opts.append(f"credentials={cred_file}")
        else:
            base_opts.append("guest")
        vers_attempts = [vers] if vers else ["3.0", "2.1", "2.0"]
        last_output = ""
        last_opts = []
        for v in vers_attempts:
            opts = base_opts.copy()
            if v:
                sanitize_component(v)
                opts.append(f"vers={v}")
            cmd = ["mount", "-t", "cifs", unc, str(mountpoint), "-o", ",".join(opts)]
            res = subprocess.run(cmd, capture_output=True, text=True)
            output = (res.stderr or res.stdout or "").strip()
            public_opts = [o for o in opts if not o.startswith("credentials=")]
            msg = f"UNC={unc} opts={';'.join(public_opts)} msg={output or res.returncode}"
            if res.returncode == 0:
                return 0, msg
            last_output = msg
            last_opts = public_opts
        return 1, last_output or f"UNC={unc} opts={';'.join(last_opts) or 'none'} msg=mount failed"
    finally:
        if cred_file and cred_file.exists():
            try:
                cred_file.unlink()
            except Exception:
                pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True, help="smb://server/share[/path]")
    parser.add_argument("--mountpoint", required=True, help="mount point path")
    parser.add_argument("--username", default="", help="SMB username")
    parser.add_argument("--password", default="", help="SMB password")
    parser.add_argument("--domain", default="", help="SMB domain (optional)")
    parser.add_argument("--vers", default="", help="SMB protocol version (optional, e.g., 3.0)")
    args = parser.parse_args()
    try:
        unc = normalize_smb_url(args.url)
        code, msg = run_mount(unc, Path(args.mountpoint), args.username or "", args.password or "", args.domain or None, args.vers or None)
        if code != 0:
            sys.stderr.write(msg + "\n")
            sys.exit(code)
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(str(exc) + "\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
