# autoencoder.py
"""
autoencoder.py

This script serves as the entry point for the video encoding application. It initializes the Scanner and (optionally) Encoder classes and orchestrates the process of finding and encoding video files.

Required Python version: >=3.7
Dependencies:
- HandBrakeCLI (installed on the system and available on PATH)
"""
from pathlib import Path
import json
import os
import time
import logging
import logging.handlers
import subprocess
import pathlib
import re
import shutil
import threading
import uuid
from typing import Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from scanner import Scanner, EXCLUDED_SCAN_PATHS
from encoder import Encoder  # kept as a fallback if needed
from status_tracker import StatusTracker
from smb_allowlist import enforce_smb_allowlist, load_smb_allowlist, save_smb_allowlist, remove_from_allowlist
from web_server import start_web_server

# locate config in the state volume (seeded from repo config.json on first run)
STATE_DIR = Path("/var/lib/autoencoder/state")
CONFIG_PATH = STATE_DIR / "config.json"
FALLBACK_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.json"
LOG_DIR = Path(__file__).resolve().parents[1] / "logs"
LOG_FILE = LOG_DIR / "app.log"
WEB_PORT = 5959
SMB_MOUNT_ROOT = Path("/mnt/smb")
USB_SEEN_PATH = STATE_DIR / "usb_seen.json"
# map staged USB path -> original source path
USB_ORIGIN_MAP: Dict[str, str] = {}

DEFAULT_CONFIG = {
    "search_path": None,
    "output_dir": "/mnt/output",
    "rip_dir": "/mnt/ripped",
    "final_dir": "",
    "profile": "handbrake",
    "handbrake_presets": [],
    "max_threads": 4,
    "rescan_interval": 30,
    "min_size_mb": 100,
    "low_bitrate_auto_proceed": False,
    "low_bitrate_auto_skip": False,
    "video_extensions": [".mp4", ".mkv", ".avi", ".mov", ".flv", ".wmv", ".m4v"],
    "smb_staging_dir": "/mnt/smb_staging",
    "usb_staging_dir": "/mnt/usb_staging",
    "auth_user": "admin",
    "auth_password": "changeme",
    "handbrake": {
        "encoder": "x264",
        "quality": 20,
        "video_bitrate_kbps": None,
        "two_pass": False,
        "audio_offset_ms": 0,
        "audio_bitrate_kbps": 128,
        "audio_mode": "encode",  # encode | copy | auto_dolby
        "audio_encoder": "av_aac",
        "audio_mixdown": "",
        "audio_drc": None,
        "audio_gain": None,
        "audio_samplerate": "",
        "audio_lang_list": [],
        "audio_track_list": "",
        "audio_all": False,
        "subtitle_mode": "none",  # none | copy_all | burn_forced
        "extra_args": [],
        "extension": ".mkv"
    },
    "handbrake_dvd": {
        "encoder": "x264",
        "quality": 20,
        "video_bitrate_kbps": None,
        "two_pass": False,
        "audio_offset_ms": 0,
        "width": 1920,
        "height": 1080,
        "extension": ".mkv",
        "extra_args": [],
        "audio_bitrate_kbps": 128,
        "audio_mode": "encode",
        "audio_encoder": "av_aac",
        "audio_mixdown": "",
        "audio_drc": None,
        "audio_gain": None,
        "audio_samplerate": "",
        "audio_lang_list": [],
        "audio_track_list": "",
        "audio_all": False,
        "subtitle_mode": "none"
    },
    "handbrake_br": {
        "encoder": "x264",
        "quality": 25,
        "video_bitrate_kbps": None,
        "two_pass": False,
        "audio_offset_ms": 0,
        "width": 3840,
        "height": 2160,
        "extension": ".mkv",
        "extra_args": [],
        "audio_bitrate_kbps": 128,
        "audio_mode": "encode",
        "audio_encoder": "av_aac",
        "audio_mixdown": "",
        "audio_drc": None,
        "audio_gain": None,
        "audio_samplerate": "",
        "audio_lang_list": [],
        "audio_track_list": "",
        "audio_all": False,
        "subtitle_mode": "none"
    },
    "makemkv_minlength": 1200,
    "makemkv_titles": [],
    "makemkv_audio_langs": [],
    "makemkv_subtitle_langs": [],
    "makemkv_keep_ripped": False,
    "makemkv_preferred_audio_langs": ["eng"],
    "makemkv_preferred_subtitle_langs": ["eng"],
    "makemkv_exclude_commentary": False,
    "makemkv_prefer_surround": True,
    "makemkv_auto_rip": False,
}

class ConfigManager:
    def __init__(self, path: Path):
        self._ensure_seed()
        self.path = path
        self.lock = threading.Lock()

    def _ensure_seed(self):
        """Ensure the persisted config file exists; seed from fallback config.json if missing."""
        try:
            CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            if not CONFIG_PATH.exists():
                if FALLBACK_CONFIG_PATH.exists():
                    shutil.copy2(FALLBACK_CONFIG_PATH, CONFIG_PATH)
                else:
                    CONFIG_PATH.touch()
        except Exception:
            logging.exception("Failed to seed config file at %s", CONFIG_PATH)

    def read(self) -> Dict[str, Any]:
        with self.lock:
            return load_config(self.path)

    def update(self, data: Dict[str, Any]) -> Dict[str, Any]:
        with self.lock:
            cfg = load_config(self.path)
            for field in [
                "output_dir",
                "rip_dir",
                "final_dir",
                "max_threads",
                "rescan_interval",
                "min_size_mb",
                "makemkv_minlength",
                "smb_staging_dir",
                "usb_staging_dir",
                "auth_user",
                "auth_password",
                "makemkv_titles",
                "makemkv_audio_langs",
                "makemkv_subtitle_langs",
                "makemkv_keep_ripped",
                "makemkv_preferred_audio_langs",
                "makemkv_preferred_subtitle_langs",
                "makemkv_exclude_commentary",
                "makemkv_prefer_surround",
                "makemkv_auto_rip",
                "low_bitrate_auto_proceed",
                "low_bitrate_auto_skip",
                "search_path",
                "profile",
            ]:
                if field in data and data[field] is not None:
                    cfg[field] = data[field]
            for key in ["handbrake", "handbrake_dvd", "handbrake_br"]:
                hb_data = data.get(key)
                if isinstance(hb_data, dict):
                    if key not in cfg or not isinstance(cfg.get(key), dict):
                        cfg[key] = {}
                    for k, v in hb_data.items():
                        if v is not None:
                            cfg[key][k] = v
            try:
                with self.path.open("w", encoding="utf-8") as f:
                    json.dump(cfg, f, indent=2)
            except Exception:
                logging.exception("Failed to write config to %s", self.path)
            return load_config(self.path)

def load_config(path: Path):
    try:
        with path.open("r", encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception:
        cfg = {}
    # merge defaults (shallow merge is sufficient for this shape)
    merged = DEFAULT_CONFIG.copy()
    merged.update({k: v for k, v in cfg.items() if v is not None})
    # ensure output_dir is a string path
    merged["output_dir"] = str(Path(merged["output_dir"]))
    merged["smb_staging_dir"] = str(Path(merged.get("smb_staging_dir", DEFAULT_CONFIG["smb_staging_dir"])))
    merged["usb_staging_dir"] = str(Path(merged.get("usb_staging_dir", DEFAULT_CONFIG["usb_staging_dir"])))
    merged["auth_user"] = merged.get("auth_user", DEFAULT_CONFIG["auth_user"])
    merged["auth_password"] = merged.get("auth_password", DEFAULT_CONFIG["auth_password"])
    # ensure handbrake dict exists
    for hb_key in ["handbrake", "handbrake_dvd", "handbrake_br"]:
        if hb_key not in merged or not isinstance(merged.get(hb_key), dict):
            merged[hb_key] = DEFAULT_CONFIG.get(hb_key, {}).copy()
        else:
            hb = DEFAULT_CONFIG.get(hb_key, {}).copy()
            hb.update({k: v for k, v in merged[hb_key].items() if v is not None})
            merged[hb_key] = hb
        # normalize HB list fields
        for list_key in ["audio_lang_list"]:
            val = merged[hb_key].get(list_key, [])
            if isinstance(val, str):
                val = [v.strip() for v in val.split(",") if v.strip()]
            elif isinstance(val, list):
                val = [str(v).strip() for v in val if str(v).strip()]
            else:
                val = []
            merged[hb_key][list_key] = val
        for str_key in ["audio_track_list", "audio_mixdown", "audio_samplerate", "audio_encoder"]:
            v = merged[hb_key].get(str_key, "")
            merged[hb_key][str_key] = "" if v is None else str(v)
        for num_key in ["audio_drc", "audio_gain"]:
            val = merged[hb_key].get(num_key)
            try:
                merged[hb_key][num_key] = float(val) if val is not None else None
            except Exception:
                merged[hb_key][num_key] = None
    if "handbrake_presets" not in merged or not isinstance(merged.get("handbrake_presets"), list):
        merged["handbrake_presets"] = []
    if "makemkv_minlength" not in merged:
        merged["makemkv_minlength"] = DEFAULT_CONFIG["makemkv_minlength"]
    for key in ["makemkv_titles", "makemkv_audio_langs", "makemkv_subtitle_langs", "makemkv_preferred_audio_langs", "makemkv_preferred_subtitle_langs"]:
        val = merged.get(key, [])
        if isinstance(val, str):
            val = [v.strip() for v in val.split(",") if v.strip()]
        elif isinstance(val, list):
            val = [str(v).strip() for v in val if str(v).strip()]
        else:
            val = []
        merged[key] = val
    merged["makemkv_keep_ripped"] = bool(merged.get("makemkv_keep_ripped"))
    merged["makemkv_exclude_commentary"] = bool(merged.get("makemkv_exclude_commentary"))
    merged["makemkv_prefer_surround"] = bool(merged.get("makemkv_prefer_surround"))
    merged["makemkv_auto_rip"] = bool(merged.get("makemkv_auto_rip"))
    merged["low_bitrate_auto_proceed"] = bool(merged.get("low_bitrate_auto_proceed"))
    merged["low_bitrate_auto_skip"] = bool(merged.get("low_bitrate_auto_skip"))
    return merged

def load_usb_seen() -> Dict[str, Dict[str, float]]:
    try:
        with USB_SEEN_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    except FileNotFoundError:
        return {}
    except Exception:
        logging.debug("Failed to load USB seen file; starting fresh", exc_info=True)
    return {}


def save_usb_seen(data: Dict[str, Dict[str, float]]) -> None:
    try:
        USB_SEEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        with USB_SEEN_PATH.open("w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        logging.debug("Failed to save USB seen file", exc_info=True)


def is_usb_already_encoded(src: Path, src_stat=None) -> bool:
    if not src:
        return False
    try:
        st = src.stat() if src_stat is None else src_stat
    except Exception:
        return False
    seen = load_usb_seen()
    entry = seen.get(str(src))
    if not entry:
        return False
    try:
        size_match = entry.get("size") == st.st_size
        mtime_match = abs(entry.get("mtime", 0) - st.st_mtime) < 1
        return size_match and mtime_match
    except Exception:
        return False


def mark_usb_encoded(src: Path, src_stat=None) -> None:
    if not src:
        return
    try:
        st = src.stat() if src_stat is None else src_stat
    except Exception:
        return
    seen = load_usb_seen()
    seen[str(src)] = {"size": st.st_size, "mtime": st.st_mtime}
    save_usb_seen(seen)


def setup_logging():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    handlers = [
        logging.StreamHandler(),
        logging.handlers.RotatingFileHandler(
            LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=2, encoding="utf-8"
        ),
    ]
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)s: %(message)s",
        handlers=handlers,
    )

def ensure_smb_root():
    try:
        SMB_MOUNT_ROOT.mkdir(parents=True, exist_ok=True)
    except Exception:
        logging.debug("Failed to create SMB mount root %s", SMB_MOUNT_ROOT, exc_info=True)

def rip_disc(
    disc_index,
    output_dir_path,
    min_length=1800,
    status_tracker: Optional[StatusTracker] = None,
    titles=None,
    audio_langs=None,
    subtitle_langs=None,
):
    """
    Rips a Blu-ray disc using MakeMKV CLI.
    Returns (path, reused_existing) where path is the first output file if successful, or (None, False) on failure.
    """
    # return "/mnt/md0/ripped_discs/Interstellar_t00.mkv"
    logger = logging.getLogger(__name__)
    output_dir = output_dir_path.as_posix()
    title_list = []
    if titles:
        try:
            title_list = [str(t).strip() for t in titles if str(t).strip()]
        except Exception:
            title_list = []
    if title_list:
        title_arg = ",".join(title_list)
    else:
        title_arg = "all"
    cmd = [
        "makemkvcon", "mkv", f"disc:{disc_index}", title_arg, output_dir,
        f"--minlength={min_length}", "--progress=-same"
    ]
    lang_list_audio = []
    lang_list_subs = []
    try:
        if audio_langs:
            lang_list_audio = [str(l).strip() for l in audio_langs if str(l).strip()]
        if subtitle_langs:
            lang_list_subs = [str(l).strip() for l in subtitle_langs if str(l).strip()]
    except Exception:
        lang_list_audio = []
        lang_list_subs = []
    if lang_list_audio:
        cmd.append(f"--audio={','.join(lang_list_audio)}")
    if lang_list_subs:
        cmd.append(f"--subtitle={','.join(lang_list_subs)}")

    # Check for existing MKVs; reuse newest if present
    existing_mkvs = sorted(output_dir_path.glob("*.mkv"), key=os.path.getmtime)
    if existing_mkvs:
        latest = existing_mkvs[-1].resolve()
        msg_existing = f"⚠️  Found existing MKV file: {latest}\nReusing existing rip."
        print(msg_existing)
        if status_tracker:
            status_tracker.add_event(f"Using existing ripped MKV: {latest}")
        return str(latest), True

    msg = f"📀 Running: {' '.join(cmd)}"
    print(msg)
    if status_tracker:
        status_tracker.add_event(
            f"MakeMKV rip started (disc {disc_index}; titles={title_arg}; audio={','.join(lang_list_audio) or 'all'}; subs={','.join(lang_list_subs) or 'all'})"
        )

    try:
        result = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        # Iterate lines as they arrive and log them
        if result.stdout is not None:
            for line in result.stdout:
                logger.info(line.rstrip())
        rc = result.wait()
        logger.debug("exited with code %s", rc)
    except FileNotFoundError:
        print("❌ Error: makemkvcon not found. Is MakeMKV installed?")
        return None, False

    if status_tracker:
        if rc == 0:
            status_tracker.add_event(f"MakeMKV rip complete (disc {disc_index})")
        else:
            status_tracker.add_event(f"MakeMKV rip failed (disc {disc_index})", level="error")

    # Print (or log) the MakeMKV output
    print(result.stdout)

    # Check for success
    if result.returncode != 0:
        print(f"❌ MakeMKV failed with code {result.returncode}.")
        return None, False

    print("✅ MakeMKV completed successfully.")

    # Look for any .mkv files in the output directory
    mkv_files = sorted(output_dir_path.glob("*.mkv"), key=os.path.getmtime)

    if not mkv_files:
        print("⚠️  No MKV files found in output directory.")
        return None, False

    # Return the most recent or first MKV file path
    first_file = str(mkv_files[-1].resolve())
    print(f"🎬 Output file: {first_file}")
    return first_file, False

def get_disc_number():
    """
    Returns the first detected MakeMKV disc index as an integer.
    If no disc is found, returns None.
    """
    try:
        # Query MakeMKV for available drives
        result = subprocess.run(
            ["makemkvcon", "-r", "info", "disc:9999"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=True
        )
    except subprocess.CalledProcessError as e:
        print("Error running makemkvcon:", e.output.strip())
        return None

    output = result.stdout.strip()

    # Regex matches lines like:
    # DRV:0,0,999,0,"BD-RE HL-DT-ST BD-RE  WH16NS40 1.05","/dev/sr0"
    pattern = re.compile(r'DRV:(\d+),\d+,\d+,\d+,"([^"]+)","([^"]+)"')

    match = pattern.search(output)
    if match:
        disc_index = int(match.group(1))
        drive_name = match.group(2)
        device_path = match.group(3)
        print(f"Found disc in drive '{drive_name}' ({device_path}) — disc:{disc_index}")
        return disc_index

    print("No disc detected.")
    return None

def safe_move(src: Path, dst: Path) -> bool:
    src = Path(src)
    dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)

    try:
        # Fast path: same filesystem → atomic replace
        os.replace(src, dst)
        return True
    except OSError:
        pass

    # Cross-device: copy then atomically swap into place, then remove source
    try:
        tmp = dst.with_suffix(dst.suffix + ".part")
        shutil.copy2(src, tmp)     # preserves mtime/perm when possible
        os.replace(tmp, dst)       # atomic at destination
        os.unlink(src)             # remove original
        return True
    except Exception as e:
        logging.error("Failed to move %s to %s: %s", src, dst, e)
        return False


def find_external_subtitle(input_path: Path) -> Optional[Path]:
    """
    Find a sidecar .srt matching the video file (exact stem or stem.language).
    Returns the first matching file if present.
    """
    if not input_path:
        return None
    stem = input_path.stem
    parent = input_path.parent
    exact = parent / f"{stem}.srt"
    if exact.exists():
        return exact
    # allow stem.lang.srt (e.g., movie.eng.srt)
    for cand in sorted(parent.glob(f"{stem}.*.srt")):
        if cand.is_file():
            return cand
    return None


def cleanup_sidecars_and_allowlist(src: Path):
    """Remove sidecar .srt files and clear allowlist entries for the source and sidecars."""
    if not src:
        return
    names = [src.name]
    try:
        stem = src.stem
        parent = src.parent
        # exact match
        exact = parent / f"{stem}.srt"
        if exact.exists():
            names.append(exact.name)
            try:
                exact.unlink()
            except Exception:
                pass
        # stem.lang.srt
        for cand in parent.glob(f"{stem}.*.srt"):
            if cand.is_file():
                names.append(cand.name)
                try:
                    cand.unlink()
                except Exception:
                    pass
    finally:
        remove_from_allowlist(names)


def cleanup_usb_staging(src: Path, config: dict):
    """Remove staged USB copy (and sidecars) if it lives in the usb_staging_dir."""
    try:
        staging_dir = Path(config.get("usb_staging_dir", "/mnt/usb_staging"))
    except Exception:
        staging_dir = Path("/mnt/usb_staging")
    try:
        if src.is_file() and staging_dir in src.parents:
            # remove sidecars in staging too
            cleanup_sidecars_and_allowlist(src)
            src.unlink()
            logging.info("Deleted staged USB file after encode: %s", src)
    except Exception:
        logging.debug("Failed to delete staged USB file %s", src, exc_info=True)


def stage_usb_file(src: Path, staging_dir: Path, status_tracker: Optional[StatusTracker] = None) -> Path:
    """Copy a USB-sourced file (and matching sidecar .srt) into staging and return the staged path."""
    staging_dir.mkdir(parents=True, exist_ok=True)
    base = src.stem
    ext = src.suffix
    dest = staging_dir / f"{base}{ext}"
    try:
        src_stat = src.stat()
    except Exception:
        src_stat = None

    if is_usb_already_encoded(src, src_stat):
        if status_tracker:
            status_tracker.add_event(f"Skipping already-encoded USB file: {src}")
        return None

    def pick_dest(existing_dest: Path) -> Path:
        if not existing_dest.exists():
            return existing_dest
        # reuse if it matches size/mtime to avoid duplicate copies
        try:
            if src_stat and existing_dest.stat().st_size == src_stat.st_size:
                return existing_dest
        except Exception:
            pass
        idx = 1
        candidate = existing_dest
        while candidate.exists():
            candidate = staging_dir / f"{base}({idx}){ext}"
            idx += 1
        return candidate

    dest = pick_dest(dest)
    copied = False
    if not dest.exists():
        shutil.copy2(src, dest)
        copied = True

    # copy matching sidecar subtitle if present
    sidecar = find_external_subtitle(src)
    if sidecar:
        sidecar_dest = staging_dir / sidecar.name
        try:
            if not sidecar_dest.exists():
                shutil.copy2(sidecar, sidecar_dest)
        except Exception:
            if status_tracker:
                status_tracker.add_event(f"Failed to copy USB sidecar: {sidecar}", level="error")

    if copied and status_tracker:
        status_tracker.add_event(f"Staged USB file: {src} -> {dest}")
    # remember origin so we can mark it encoded after success
    USB_ORIGIN_MAP[str(dest)] = str(src)
    return dest


def staging_has_files(staging_dir: Path) -> bool:
    try:
        return any(staging_dir.iterdir())
    except FileNotFoundError:
        return False


def process_pending_smb(status_tracker: StatusTracker, staging_dir: Path, config: dict):
    if not status_tracker.has_smb_pending():
        return
    if status_tracker.has_active_nonqueued():
        return
    if staging_has_files(staging_dir):
        return
    entry = status_tracker.pop_next_smb_pending()
    if not entry:
        return
    src = Path(entry.get("source", ""))
    dest = Path(entry.get("dest", staging_dir / src.name))
    sidecar = entry.get("sidecar")
    dest_root = staging_dir
    dest_root.mkdir(parents=True, exist_ok=True)
    try:
        allowlist = load_smb_allowlist()
        allowlist.add(dest.name)
        if sidecar:
            allowlist.add(Path(sidecar).name)
        save_smb_allowlist(allowlist)
        shutil.copy2(src, dest)
        if sidecar:
            try:
                shutil.copy2(Path(sidecar), dest_root / Path(sidecar).name)
                status_tracker.add_event(f"Copied queued external subtitle: {sidecar}")
            except Exception:
                status_tracker.add_event(f"Failed to copy queued external subtitle: {sidecar}", level="error")
        status_tracker.add_manual_file(str(dest))
        status_tracker.add_event(f"Copied queued SMB file after encode idle: {src} -> {dest}")
        if not status_tracker.has_active(str(dest)):
            dest_hint = compute_output_path(str(dest), config, Path(config.get("output_dir")))
            status_tracker.start(str(dest), str(dest_hint), info=None, state="queued")
    except Exception:
        status_tracker.add_event(f"Failed to copy queued SMB file: {src} -> {dest}", level="error")


def compute_output_path(video_file: str, config: Dict[str, Any], output_dir: Path) -> Path:
    config_str = config.get("profile", "ffmpeg")
    is_dvd = False
    is_bluray = False
    if any(s in video_file.lower() for s in ["bdmv", "bluray"]):
        is_bluray = True
        config_str = "handbrake_br"
    elif any(s in video_file.lower() for s in ["video_ts"]):
        is_dvd = True
        config_str = "handbrake_dvd"

    hb_opts = config.get(config_str, {})
    extension = hb_opts.get("extension", ".mkv")

    src = Path(video_file)

    def unique_name(base_dir: Path, base: str, ext: str) -> Path:
        candidate = base_dir / f"{base}{ext}"
        idx = 1
        while candidate.exists():
            candidate = base_dir / f"{base}({idx}){ext}"
            idx += 1
        return candidate

    if is_dvd:
        base = src.parent.name
    elif is_bluray:
        base = src.parent.parent.name
    else:
        base = src.stem

    return unique_name(output_dir, base, extension)


def probe_source_info(path: Path) -> Optional[str]:
    try:
        if not path.is_file():
            return None
        proc = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,bit_rate,codec_name", "-show_entries", "format=bit_rate", "-of", "json", str(path)],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0 or not proc.stdout:
            return None
        data = json.loads(proc.stdout)
        stream = (data.get("streams") or [{}])[0]
        fmt = data.get("format") or {}
        width = stream.get("width")
        height = stream.get("height")
        codec = stream.get("codec_name")
        br = stream.get("bit_rate") or fmt.get("bit_rate")
        if br:
            try:
                mbps = round(int(br) / 1_000_000, 2)
            except Exception:
                mbps = None
        else:
            mbps = None
        parts = []
        if width and height:
            parts.append(f"{width}x{height}")
        if codec:
            parts.append(codec)
        if mbps is not None:
            parts.append(f"{mbps} Mbps")
        return "Source: " + " ".join(parts) if parts else None
    except Exception:
        return None

def probe_source_bitrate_kbps(path: Path) -> Optional[float]:
    try:
        if not path.is_file():
            return None
        proc = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=bit_rate", "-show_entries", "format=bit_rate", "-of", "json", str(path)],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0 or not proc.stdout:
            return None
        data = json.loads(proc.stdout)
        stream = (data.get("streams") or [{}])[0]
        fmt = data.get("format") or {}
        br = stream.get("bit_rate") or fmt.get("bit_rate")
        if br:
            try:
                return int(br) / 1000.0
            except Exception:
                return None
    except Exception:
        return None
    return None

def probe_audio_stream(path: Path) -> Optional[dict]:
    try:
        if not path.is_file():
            return None
        proc = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "a:0",
                "-show_entries",
                "stream=codec_name,channels",
                "-of",
                "json",
                str(path),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0 or not proc.stdout:
            return None
        data = json.loads(proc.stdout)
        stream = (data.get("streams") or [{}])[0]
        codec = stream.get("codec_name")
        channels = stream.get("channels")
        try:
            channels = int(channels) if channels is not None else None
        except Exception:
            channels = None
        return {"codec": codec, "channels": channels}
    except Exception:
        return None

def scan_disc_info(disc_index: int) -> Optional[dict]:
    """
    Runs makemkvcon info to gather titles/tracks.
    Returns a dict with raw text plus parsed titles/audio/subs when possible.
    """
    try:
        res = subprocess.run(
            ["makemkvcon", "-r", "info", f"disc:{disc_index}"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return None
    if res.returncode != 0 and not res.stdout:
        return None
    raw = res.stdout or res.stderr or ""
    titles = []
    for line in raw.splitlines():
        if line.startswith("TINFO"):
            # Format: TINFO:<title>,<type>,..., "<value>"
            parts = line.split(",")
            if len(parts) < 3:
                continue
            try:
                t_id = int(parts[1])
            except Exception:
                continue
            if len(parts) >= 4:
                val_part = ",".join(parts[3:])
            else:
                val_part = ""
            if "0,\"" in line and "\"M" in line:
                pass
            titles.append({"line": line.strip(), "title_id": t_id})
    return {"raw": raw, "titles": titles}

def estimate_target_bitrate_kbps(config_str: str, hb_opts: dict) -> Optional[float]:
    if hb_opts.get("video_bitrate_kbps"):
        try:
            return float(hb_opts.get("video_bitrate_kbps"))
        except Exception:
            pass
    # Approximate map from RF to kbps (from UI hints)
    rf_map = {
        16: 4000, 18: 3500, 20: 3000, 22: 2500, 24: 2000,
        25: 1750, 26: 1500, 28: 1200, 30: 1000
    }
    try:
        q = int(hb_opts.get("quality"))
        return rf_map.get(q)
    except Exception:
        return None

def run_encoder(input_path: str, output_path: str, opts: dict, ffmpeg: bool, status_tracker: Optional[StatusTracker] = None, job_id: Optional[str] = None) -> bool:
    """
    Run HandBrakeCLI or ffmpeg and stream its stdout/stderr to the logger in real time.
    Returns True on success, False otherwise.
    """
    logger = logging.getLogger(__name__)
    job_key = job_id or str(input_path)
    encoder = opts.get("encoder", "x264")
    quality = opts.get("quality", "")
    width = opts.get("width", 1920)
    profile = opts.get("profile", "")
    height = opts.get("height", 1080)
    video = opts.get("video", "")
    audio = opts.get("audio", "")
    audio_mode = opts.get("audio_mode", "encode")
    audio_encoder = opts.get("audio_encoder", "av_aac")
    audio_bitrate_kbps = opts.get("audio_bitrate_kbps")
    audio_all = bool(opts.get("audio_all"))
    audio_mixdown = opts.get("audio_mixdown") or ""
    audio_drc = opts.get("audio_drc")
    audio_gain = opts.get("audio_gain")
    audio_samplerate = opts.get("audio_samplerate") or ""
    audio_lang_list = opts.get("audio_lang_list") or []
    audio_track_list = opts.get("audio_track_list") or ""
    subtitle_mode = opts.get("subtitle_mode", "none")
    audio_offset_ms = opts.get("audio_offset_ms")
    apply_audio_offset = bool(opts.get("_apply_audio_offset"))
    temp_offset_path = None
    video_bitrate_kbps = opts.get("video_bitrate_kbps")
    two_pass = bool(opts.get("two_pass"))
    hwdev = opts.get("hwdev", "")
    filterdev = opts.get("filterdev", "")
    #audio_bitrate_kbps = opts.get("audio_bitrate_kbps", 128)
    extra = opts.get("extra_args", []) or []

    if ffmpeg:
        cmd = [
            "ffmpeg",
            "-y",  # overwrite output
            "-i", str(input_path),
            "-c:v", str(encoder),
            "-vf", str(video)
        ]
        if filterdev != "":
            cmd.insert(1, "-filter_hw_device")
            cmd.insert(2, str(filterdev))
        if hwdev != "":
            cmd.insert(1, "-init_hw_device")
            cmd.insert(2, str(hwdev))
        if quality != "":
            cmd.append("-global_quality")
            cmd.append(str(quality))
        if profile != "":
            cmd.append("-profile:v")
            cmd.append(str(profile))
        if audio != "":
            cmd.append("-c:a")
            cmd.append(str(audio))
        cmd.append(str(output_path))
        logger.info("Running ffmpeg: %s", " ".join(cmd))
    else:
        if apply_audio_offset and audio_offset_ms not in (None, "", 0, "0"):
            try:
                offset_sec = float(audio_offset_ms) / 1000.0
                temp_offset_path = Path("/tmp") / f"hb_offset_{uuid.uuid4().hex}{Path(input_path).suffix}"
                pre_cmd = [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(input_path),
                    "-itsoffset",
                    str(offset_sec),
                    "-i",
                    str(input_path),
                    "-map",
                    "0:v",
                    "-map",
                    "1:a?",
                    "-map",
                    "0:s?",
                    "-c:v",
                    "copy",
                    "-c:a",
                    "copy",
                    "-c:s",
                    "copy",
                    str(temp_offset_path),
                ]
                logger.info("Pre-shifting audio via ffmpeg: %s", " ".join(map(str, pre_cmd)))
                pre_rc = subprocess.run(pre_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                logger.info(pre_rc.stdout)
                if pre_rc.returncode != 0:
                    logger.error("Audio offset prep failed (ffmpeg). Skipping offset. rc=%s", pre_rc.returncode)
                    temp_offset_path = None
                else:
                    input_path = str(temp_offset_path)
            except Exception:
                logger.exception("Audio offset prep failed; skipping offset")
                temp_offset_path = None
        cmd = [
            "HandBrakeCLI",
            "-i", str(input_path),
            "-o", str(output_path),
            "-e", str(encoder),
            "--width", str(width),
            "--height", str(height)
            #"-B", str(int(audio_bitrate_kbps))
        ]
        if video_bitrate_kbps:
            try:
                cmd.extend(["-b", str(int(video_bitrate_kbps))])
            except Exception:
                cmd.extend(["-b", str(video_bitrate_kbps)])
            if two_pass:
                cmd.append("--two-pass")
        else:
            cmd.extend(["-q", str(quality)])
        # Auto Dolby logic: copy existing AC3/E-AC3, otherwise encode to E-AC3 (no upmix when channels <5)
        source_audio = None
        eff_audio_mode = audio_mode
        eff_audio_encoder = audio_encoder
        eff_audio_mixdown = audio_mixdown
        if audio_mode == "auto_dolby":
            source_audio = probe_audio_stream(Path(input_path))
            codec = (source_audio or {}).get("codec")
            channels = (source_audio or {}).get("channels")
            if codec in {"ac3", "eac3"}:
                eff_audio_mode = "copy"
            else:
                eff_audio_mode = "encode"
                eff_audio_encoder = "eac3"
                if channels is not None and channels >= 5 and not eff_audio_mixdown:
                    eff_audio_mixdown = "5point1"

        if audio_track_list:
            cmd.extend(["--audio", str(audio_track_list)])
        if audio_lang_list:
            cmd.extend(["--audio-lang-list", ",".join(audio_lang_list)])
        if eff_audio_mode == "copy":
            cmd.extend(["-E", "copy"])
            if audio_all:
                cmd.append("--all-audio")
        else:
            cmd.extend(["-E", str(eff_audio_encoder or "av_aac")])
            if eff_audio_mixdown:
                cmd.extend(["-6", str(eff_audio_mixdown)])
            if audio_samplerate:
                cmd.extend(["-R", str(audio_samplerate)])
            if audio_drc is not None:
                try:
                    cmd.extend(["--drc", str(float(audio_drc))])
                except Exception:
                    pass
            if audio_gain is not None:
                try:
                    cmd.extend(["--gain", str(float(audio_gain))])
                except Exception:
                    pass
            if audio_bitrate_kbps:
                try:
                    cmd.extend(["-B", str(int(audio_bitrate_kbps))])
                except Exception:
                    cmd.extend(["-B", str(audio_bitrate_kbps)])
            if audio_all:
                cmd.append("--all-audio")
        external_sub = find_external_subtitle(Path(input_path))
        if external_sub:
            cmd.extend(["--srt-file", str(external_sub), "--srt-default", "1"])
            if status_tracker:
                status_tracker.add_event(f"Included external subtitle: {external_sub}")
        if subtitle_mode == "copy_all":
            cmd.append("--all-subtitles")
        elif subtitle_mode == "burn_forced":
            cmd.extend(["--subtitle", "1", "--subtitle-burned"])
        cmd.extend(map(str, extra))
        logger.info("Running HandBrakeCLI: %s", " ".join(cmd))
    try:
        if status_tracker:
            status_tracker.add_event(f"Encoding started: {input_path}")
        # Stream combined stdout+stderr so progress and messages appear live
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        if status_tracker:
            status_tracker.register_proc(job_key, proc)
        # Iterate output chunks (handles HandBrake carriage-return updates)
        if proc.stdout is not None:
            import re
            progress_re = re.compile(r'([0-9]{1,3}(?:[.,][0-9]{1,2})?)\s*%')
            eta_re = re.compile(r'ETA\s+([0-9hms:]+)', re.IGNORECASE)

            def parse_eta_seconds(token: str) -> Optional[int]:
                try:
                    token = token.strip()
                    if not token:
                        return None
                    # Handle HH:MM:SS or MM:SS
                    if ":" in token:
                        parts = [int(p) for p in token.split(":") if p != ""]
                        if len(parts) == 3:
                            h, m, s = parts
                        elif len(parts) == 2:
                            h = 0
                            m, s = parts
                        else:
                            return None
                        return h * 3600 + m * 60 + s
                    # Handle 1h2m3s / 15m30s / 45s etc.
                    m = re.match(r'(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?', token, re.IGNORECASE)
                    if m:
                        h = int(m.group(1) or 0)
                        mn = int(m.group(2) or 0)
                        s = int(m.group(3) or 0)
                        if h or mn or s:
                            return h * 3600 + mn * 60 + s
                    return None
                except Exception:
                    return None

            buffer = ""
            for raw in iter(proc.stdout.readline, ""):
                if not raw:
                    break
                buffer += raw
                parts = re.split(r'[\r\n]+', buffer)
                buffer = parts.pop()
                for line in parts:
                    line = line.strip()
                    if not line:
                        continue
                    logger.info(line)
                    for m in progress_re.finditer(line):
                        try:
                            pct_str = m.group(1).replace(",", ".")
                            pct = float(pct_str)
                            if status_tracker:
                                status_tracker.update_progress(job_key, pct)
                        except Exception:
                            continue
                    m2 = eta_re.search(line)
                    if m2 and status_tracker:
                        try:
                            eta_val = parse_eta_seconds(m2.group(1))
                            if eta_val is not None:
                                status_tracker.update_eta(job_key, eta_val)
                        except Exception:
                            pass
            tail = buffer.strip()
            if tail:
                logger.info(tail)
        rc = proc.wait()
        logger.debug("exited with code %s", rc)
        return rc == 0
    except FileNotFoundError:
        logger.error("Encoder not found on PATH.")
        return False
    except KeyboardInterrupt:
        try:
            proc.kill()
        except Exception:
            pass
        logger.info("Encoding interrupted by user.")
        return False
    except Exception as e:
        logger.exception("Encoding run failed: %s", e)
        return False
    finally:
        if temp_offset_path:
            try:
                Path(temp_offset_path).unlink(missing_ok=True)
            except Exception:
                logger.debug("Failed to cleanup temp offset file %s", temp_offset_path, exc_info=True)

def process_video(video_file: str, config: Dict[str, Any], output_dir: Path, rip_dir: Path, encoder: Encoder, status_tracker: Optional[StatusTracker] = None, single_job_mode: bool = False) -> bool:
    config_str = config.get("profile", "ffmpeg") 
    final_dir = config.get("final_dir", "")   
    # check if dvd, bluray, or video file    
    is_dvd = False
    is_bluray = False
    if any(s in video_file.lower() for s in ["bdmv", "bluray"]):
        is_bluray = True
        config_str = "handbrake_br"
    elif any(s in video_file.lower() for s in ["video_ts"]):
        is_dvd = True 
        config_str = "handbrake_dvd"

    hb_opts = dict(config.get(config_str, {}) or {})
    extension = hb_opts.get("extension", ".mkv")

    src = Path(video_file)
    src_mtime = src.stat().st_mtime
    def unique_name(base_dir: Path, base: str, ext: str) -> Path:
        candidate = base_dir / f"{base}{ext}"
        idx = 1
        while candidate.exists():
            candidate = base_dir / f"{base}({idx}){ext}"
            idx += 1
        return candidate

    if is_dvd:
        base = src.parent.name
    elif is_bluray:
        base = src.parent.parent.name
    else:
        base = src.stem

    out_path = unique_name(output_dir, base, extension)

    dest_str = str(out_path)

    source_info = probe_source_info(Path(video_file))
    if status_tracker and not status_tracker.has_active(str(src)):
        status_tracker.add_event(f"Queued for encode: {src}")
        status_tracker.start(str(src), dest_str, info=source_info, state="queued")

    # skip if output already exists
    if out_path.exists():
        try:
            logging.info("Skipping already-encoded file: %s", out_path)
            if status_tracker:
                status_tracker.complete(str(src), True, dest_str, "Skipped (already encoded)")
            return False
        except Exception:
            logging.debug("Failed to stat files %s or %s; proceeding to encode", src, out_path)

    # If this file was previously stopped and we're asked not to re-encode, respect marker file
    stop_marker = src.with_suffix(src.suffix + ".stopped")
    if stop_marker.exists():
        logging.info("Skipping previously stopped source: %s (remove .stopped marker to re-encode)", src)
        if status_tracker:
            status_tracker.complete(str(src), False, dest_str, "Skipped (stopped marker present)")
        return False

    # if its a bluray then rip it first
    keep_ripped = bool(config.get("makemkv_keep_ripped"))
    reused_rip = False

    if is_bluray:
        logging.info("Ripping Blu-ray disc from %s", video_file)
        disc_num = get_disc_number()
        if disc_num is not None:
            minlen = int(config.get("makemkv_minlength", 1800))
            rip_titles = config.get("makemkv_titles", [])
            rip_audio_langs = config.get("makemkv_audio_langs") or config.get("makemkv_preferred_audio_langs", [])
            rip_sub_langs = config.get("makemkv_subtitle_langs") or config.get("makemkv_preferred_subtitle_langs", [])
            rip_path, reused_rip = rip_disc(
                disc_num,
                rip_dir,
                min_length=minlen,
                status_tracker=status_tracker,
                titles=rip_titles,
                audio_langs=rip_audio_langs,
                subtitle_langs=rip_sub_langs,
            )
            if rip_path is None:
                logging.error("Blu-ray ripping failed; skipping encoding for %s", video_file)
                if status_tracker:
                    status_tracker.clear_disc_info()
                    status_tracker.complete(str(src), False, dest_str, "Blu-ray rip failed")
                return False
        else:
            logging.error("No Blu-ray disc detected; skipping encoding for %s", video_file)
            if status_tracker:
                status_tracker.clear_disc_info()
                status_tracker.complete(str(src), False, dest_str, "No Blu-ray detected")
            return False

        video_file = rip_path  # use ripped path for encoding
    if video_file is None:
        if status_tracker:
            status_tracker.clear_disc_info()
            status_tracker.complete(str(src), False, dest_str, "No video file to encode")
        return False
    # prefer HandBrakeCLI; if it fails, fall back to encoder.encode_video if available
    if single_job_mode:
        hb_opts["_apply_audio_offset"] = True
    use_ffmpeg = str(config_str).startswith("ffmpeg")
    logging.info("Selected profile=%s encoder=%s ext=%s out=%s use_ffmpeg=%s audio_mode=%s audio_kbps=%s",
                 config_str, hb_opts.get("encoder"), extension, out_path, use_ffmpeg,
                 hb_opts.get("audio_mode"), hb_opts.get("audio_bitrate_kbps"))
    if status_tracker:
        status_tracker.set_state(str(src), "running")
    success = run_encoder(video_file, str(out_path), hb_opts, use_ffmpeg, status_tracker=status_tracker, job_id=str(src))
    if success:
        try:
            if not out_path.exists() or out_path.stat().st_size <= 0:
                logging.warning("Encode reported success but output is missing/empty: %s", out_path)
                success = False
        except Exception:
            logging.debug("Output existence/size check failed for %s", out_path, exc_info=True)
    if status_tracker and status_tracker.was_canceled(str(src)):
        logging.info("Job was canceled by user: %s", src)
        return False
    if not success:
        logging.warning("Encoding failed for %s -> %s; attempting Software Encoder fallback", video_file, out_path)
        if status_tracker:
            status_tracker.add_event("HandBrake failed; falling back to ffmpeg")
        try:
            ffmpeg_opts = config.get("ffmpeg_fallback", {})
            try:
                encoder.encode_video(video_file, str(out_path), ffmpeg_opts)
            except TypeError:
                encoder.encode_video(video_file, str(out_path))
            logging.info("Fallback encoder succeeded: %s -> %s", video_file, out_path)
            if status_tracker:
                status_tracker.complete(str(src), True, dest_str, "Fallback encoder succeeded")
                status_tracker.clear_disc_info()
        except Exception:
            logging.exception("Fallback encoder failed for %s", video_file)
            if status_tracker:
                status_tracker.complete(str(src), False, dest_str, "Fallback encoder failed")
            return False
    else:
        logging.info("Encoded %s -> %s (HandBrakeCLI)", video_file, out_path)
        if status_tracker and not status_tracker.was_canceled(str(src)):
            status_tracker.add_event(f"Encoding complete: {src}")
        if status_tracker:
            status_tracker.clear_disc_info()
        # move final file to final_dir if specified
        if final_dir != "":
            try:
                final_path = Path(final_dir).expanduser() / out_path.name
                if safe_move(out_path, final_path):
                    # create a blank file at the original location to indicate completion
                    out_path.touch()
                    logging.info("Moved encoded file to final directory: %s", final_path)
            except Exception:
                logging.debug("Failed to move encoded file to final directory: %s", final_dir, exc_info=True)
        if is_bluray and not keep_ripped and not reused_rip:
            try:
                # delete ripped file to save space
                rip_fp = Path(video_file)
                rip_fp.unlink()
                logging.info("Deleted ripped Blu-ray file: %s", rip_fp)
            except Exception:
                logging.debug("Failed to delete ripped Blu-ray file: %s", video_file, exc_info=True)
        elif is_bluray and (keep_ripped or reused_rip):
            logging.info("Keeping ripped Blu-ray file per config: %s", video_file)
        # Remove source file after a successful encode to avoid re-encoding
        if not is_dvd and not is_bluray:
            try:
                if src.is_file():
                    src.unlink()
                    logging.info("Deleted source file after successful encode: %s", src)
            except Exception:
                logging.debug("Failed to delete source file %s", src, exc_info=True)
            cleanup_sidecars_and_allowlist(src)
            # mark original USB source as encoded to avoid re-queuing
            try:
                orig_src = USB_ORIGIN_MAP.pop(str(src), None)
                if orig_src:
                    try:
                        mark_usb_encoded(Path(orig_src))
                    except Exception:
                        logging.debug("Failed to mark USB source encoded: %s", orig_src, exc_info=True)
            except Exception:
                logging.debug("Failed USB origin bookkeeping for %s", src, exc_info=True)
            cleanup_usb_staging(src, config)
        if status_tracker:
            status_tracker.complete(str(src), True, dest_str, "Encode complete")
    return True

def main():
    setup_logging()
    ensure_smb_root()
    status_tracker = StatusTracker(LOG_FILE)
    cfg_manager = ConfigManager(CONFIG_PATH)
    start_web_server(status_tracker, config_manager=cfg_manager, port=WEB_PORT)

    config = cfg_manager.read()
    search_path = config.get("search_path")
    if search_path == '/':
        search_path = None
    output_dir = Path(config.get("output_dir"))
    output_dir.mkdir(parents=True, exist_ok=True)
    rip_dir = Path(config.get("rip_dir"))
    rip_dir.mkdir(parents=True, exist_ok=True)
    if search_path:
        scanner = Scanner(search_path=search_path)
    else:
        scanner = Scanner()
    try:
        encoder = Encoder(config=config)
    except TypeError:
        encoder = Encoder()

    last_search_path = search_path
    rescan_interval = float(config.get("rescan_interval", 30))
    last_usb_state = None  # track mount/readability status to avoid noisy repeats
    usb_state_changed_to_ready = False

    logging.info("Starting continuous scanner. search_path=%s output=%s interval=%.1fs",
                 search_path if search_path else "<auto-detect>", output_dir, rescan_interval)

    try:
        while True:
            manual_files = status_tracker.consume_manual_files()
            config = cfg_manager.read()
            rescan_interval = float(config.get("rescan_interval", 30))
            # Force single-file processing (FIFO) regardless of configured max_threads
            max_threads = 1
            search_path = config.get("search_path")
            if search_path == '/':
                search_path = None
            output_dir = Path(config.get("output_dir"))
            output_dir.mkdir(parents=True, exist_ok=True)
            rip_dir = Path(config.get("rip_dir"))
            rip_dir.mkdir(parents=True, exist_ok=True)
            if search_path != last_search_path:
                if search_path:
                    scanner = Scanner(search_path=search_path)
                else:
                    scanner = Scanner()
                last_search_path = search_path

            # decide which directories will be scanned this pass
            usb_state_changed_to_ready = False

            if search_path:
                scan_roots = [search_path]
            else:
                staging_dir = str(config.get("smb_staging_dir", "/mnt/smb_staging"))
                enforce_smb_allowlist(staging_dir, status_tracker)
                process_pending_smb(status_tracker, Path(staging_dir), config)
                base_roots = ["/mnt/input", "/mnt/dvd", "/mnt/bluray", "/mnt/usb", staging_dir]
                try:
                    mounted = scanner.ensure_mounted_candidates()
                except Exception:
                    mounted = []
                scan_roots = base_roots + mounted
                # unique preserving order
                seen = set()
                scan_roots = [x for x in scan_roots if not (x in seen or seen.add(x))]
            scan_roots = [r for r in scan_roots if r != "/mnt/output" and r not in EXCLUDED_SCAN_PATHS]

            logging.info("Scanning directories: %s", ", ".join(scan_roots) if scan_roots else "<none>")
            # debug: show mount status and a sample of contents for each scan root
            import os
            # USB health check: log once per state change if mount is missing or unreadable
            usb_ready = True
            try:
                usb_path = Path("/mnt/usb")
                usb_state = "ready"
                if not os.path.ismount(usb_path):
                    usb_state = "not-mounted"
                    usb_ready = False
                else:
                    try:
                        os.listdir(usb_path)
                    except OSError as e:
                        usb_state = f"error:{getattr(e, 'errno', 'unknown')}"
                        # keep usb_ready True so we still scan to detect recovery
                if usb_state != last_usb_state:
                    last_usb_state = usb_state
                    if usb_state == "ready":
                        usb_ready = True
                        usb_state_changed_to_ready = True
                        if status_tracker:
                            status_tracker.add_event("USB mount ready.")
                            status_tracker.set_usb_status("ready", "USB mount ready")
                    elif usb_state == "not-mounted":
                        usb_ready = False
                        if status_tracker:
                            status_tracker.add_event("USB mount missing at /mnt/usb. Re-plug or remount.", level="error")
                            status_tracker.set_usb_status("missing", "USB mount missing at /mnt/usb")
                    else:
                        if status_tracker:
                            status_tracker.add_event(f"USB mount I/O error at /mnt/usb ({usb_state}). Re-plug or fsck the stick.", level="error")
                            status_tracker.set_usb_status("error", f"I/O error at /mnt/usb ({usb_state})")
            except Exception:
                logging.debug("USB readiness check failed", exc_info=True)

            if not usb_ready and "/mnt/usb" in scan_roots and usb_state != "not-mounted":
                # If mounted but error, keep it to allow recovery on next pass; only drop when not mounted
                pass
            if usb_state == "not-mounted" and "/mnt/usb" in scan_roots:
                scan_roots = [r for r in scan_roots if r != "/mnt/usb"]
            for root in scan_roots:
                try:
                    is_m = os.path.ismount(root)
                    entries = []
                    if os.path.exists(root):
                        try:
                            entries = os.listdir(root)[:10]
                        except Exception:
                            entries = ["<unreadable>"]
                    logging.debug("Scan root: %s ismount=%s exists=%s sample=%s", root, is_m, os.path.exists(root), entries)
                except Exception:
                    logging.debug("Scan root: %s inspect failed", root)

            video_files = scanner.find_video_files(scan_roots)
            # stage USB files into a dedicated staging dir so originals remain untouched
            usb_staging_dir = Path(config.get("usb_staging_dir", "/mnt/usb_staging"))
            staged_video_files = []
            for f in video_files:
                p = Path(f)
                if str(p).startswith("/mnt/usb/"):
                    try:
                        staged = stage_usb_file(p, usb_staging_dir, status_tracker)
                        if staged is None:
                            continue
                        # register the staged file as queued if not already tracked
                        if status_tracker and not status_tracker.has_active(str(staged)):
                            dest_hint = compute_output_path(str(staged), config, Path(config.get("output_dir")))
                            status_tracker.start(str(staged), str(dest_hint), info=None, state="queued")
                        staged_video_files.append(str(staged))
                    except Exception:
                        logging.exception("Failed to stage USB file: %s", p)
                        if status_tracker:
                            status_tracker.add_event(f"Failed to stage USB file: {p}", level="error")
                else:
                    staged_video_files.append(f)
            video_files = staged_video_files
            video_files.extend(manual_files)
            for f in video_files:
                if status_tracker:
                    status_tracker.add_event(f"Detected new file: {f}")
            if not video_files:
                logging.debug("No candidate video files found on this pass.")
            # Handle manual rip requests even when no bluray files are present in the scan
            if status_tracker and status_tracker.consume_disc_rip_request():
                disc_num = get_disc_number()
                if disc_num is None:
                    status_tracker.add_event("Manual MakeMKV rip requested but no disc detected.", level="error")
                else:
                    mk_minlen = int(config.get("makemkv_minlength", 1800))
                    mk_titles = config.get("makemkv_titles", [])
                    mk_audio_langs = config.get("makemkv_audio_langs", []) or config.get("makemkv_preferred_audio_langs", [])
                    mk_sub_langs = config.get("makemkv_subtitle_langs", []) or config.get("makemkv_preferred_subtitle_langs", [])
                    rip_path, reused = rip_disc(
                        disc_num,
                        rip_dir,
                        min_length=mk_minlen,
                        status_tracker=status_tracker,
                        titles=mk_titles,
                        audio_langs=mk_audio_langs,
                        subtitle_langs=mk_sub_langs,
                    )
                    if rip_path:
                        video_files.append(str(rip_path))
                        status_tracker.set_disc_info({"disc_index": disc_num, "info": {"raw": f"Manual rip started for disc:{disc_num}"}})
                        status_tracker.add_event(f"Manual MakeMKV rip {'reused existing' if reused else 'produced'}: {rip_path}")
                    else:
                        status_tracker.add_event("Manual MakeMKV rip failed to produce output.", level="error")
            # Pre-register queued items so they appear in Active
            for f in video_files:
                try:
                    if status_tracker and not status_tracker.has_active(str(f)):
                        dest_hint = compute_output_path(f, config, output_dir)
                        status_tracker.start(str(f), str(dest_hint), info=None, state="queued")
                except Exception:
                    logging.debug("Failed to pre-register queued file %s", f, exc_info=True)
            # Disc detection / info
            try:
                bluray_present = any("bdmv" in str(f).lower() or "bluray" in str(f).lower() for f in video_files)
            except Exception:
                bluray_present = False
            auto_rip = bool(config.get("makemkv_auto_rip"))
            if bluray_present and status_tracker and not status_tracker.disc_pending():
                disc_num = get_disc_number()
                disc_info = scan_disc_info(disc_num) if disc_num is not None else None
                info_payload = {"disc_index": disc_num, "info": disc_info}
                status_tracker.set_disc_info(info_payload)
                status_tracker.add_event(f"Disc detected (index={disc_num}); auto-rip={'on' if auto_rip else 'off'}")

            active_snapshot = status_tracker.snapshot() if status_tracker else {"active": []}
            queued_active = sum(
                1 for a in active_snapshot.get("active", []) if a.get("state") in ("queued", "starting", "running")
            )
            single_job_mode = len(video_files) == 1 and queued_active == 1
            # Process sequentially (FIFO)
            for video_file in video_files:
                # Determine profile for this file
                local_profile = config.get("profile", "handbrake")
                is_dvd = any(s in video_file.lower() for s in ["video_ts"])
                is_bluray = any(s in video_file.lower() for s in ["bdmv", "bluray"])
                if is_bluray:
                    if status_tracker and not auto_rip and not status_tracker.consume_disc_rip_request():
                        # Wait for manual rip trigger
                        status_tracker.add_event("Disc present; waiting for manual rip start.")
                        continue
                    local_profile = "handbrake_br"
                elif is_dvd:
                    local_profile = "handbrake_dvd"
                hb_opts_local = config.get(local_profile, {})
                # Skip items waiting for confirmation
                if status_tracker and status_tracker.is_confirm_required(str(video_file)):
                    continue
                # Bitrate sanity check
                source_br = probe_source_bitrate_kbps(Path(video_file))
                target_br = estimate_target_bitrate_kbps(local_profile, hb_opts_local)
                if source_br and target_br and source_br < target_br and status_tracker and not status_tracker.is_confirm_ok(str(video_file)):
                    auto_proceed = bool(config.get("low_bitrate_auto_proceed"))
                    auto_skip = bool(config.get("low_bitrate_auto_skip"))
                    if auto_skip:
                        status_tracker.add_event(f"Skipped low bitrate vs target for {video_file} ({int(source_br)} kbps < {int(target_br)} kbps).")
                        status_tracker.stop_proc(str(video_file))
                        cleanup_sidecars_and_allowlist(Path(video_file))
                        continue
                    if auto_proceed:
                        status_tracker.add_event(f"Auto-proceeding despite low bitrate for {video_file} ({int(source_br)} kbps < {int(target_br)} kbps).")
                        status_tracker.add_confirm_ok(str(video_file))
                    else:
                        status_tracker.add_event(f"Low source bitrate vs target for {video_file} ({int(source_br)} kbps < {int(target_br)} kbps). Confirm to proceed.")
                        status_tracker.set_state(str(video_file), "confirm")
                        status_tracker.set_message(str(video_file), "Low bitrate; confirm to proceed.")
                        status_tracker.add_confirm_required(str(video_file))
                        continue
                try:
                    if status_tracker:
                        status_tracker.set_state(str(video_file), "starting")
                    out = process_video(video_file, config, output_dir, rip_dir, encoder, status_tracker, single_job_mode=single_job_mode)
                    print(f"✅ {video_file} → {out}")
                except Exception as e:
                    print(f"❌ {video_file}: {e}")

            sleep_for = rescan_interval
            if usb_state_changed_to_ready:
                sleep_for = 0.1
            time.sleep(sleep_for)
            # after a successful scan/pass, unmount devices the scanner mounted
            try:
                unmounted = scanner.unmount_mountpoints()
                if unmounted:
                    logging.info("Automatically unmounted: %s", ", ".join(unmounted))
            except Exception:
                logging.debug("Automatic unmount step failed", exc_info=True)
    except KeyboardInterrupt:
        logging.info("Interrupted, shutting down.")
    except Exception:
        logging.exception("Unexpected error in main loop.")
    finally:
        logging.info("Exited.")

if __name__ == "__main__":
    main()
