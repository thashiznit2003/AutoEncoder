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
from web_server import start_web_server

# locate config next to the project root
CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.json"
LOG_DIR = Path(__file__).resolve().parents[1] / "logs"
LOG_FILE = LOG_DIR / "app.log"
WEB_PORT = 5959
SMB_MOUNT_ROOT = Path("/mnt/smb")

DEFAULT_CONFIG = {
    "search_path": None,
    "output_dir": "/mnt/output",
    "rip_dir": "/mnt/ripped",
    "final_dir": "",
    "profile": "handbrake",
    "max_threads": 4,
    "rescan_interval": 30,
    "min_size_mb": 100,
    "video_extensions": [".mp4", ".mkv", ".avi", ".mov", ".flv", ".wmv", ".m4v"],
    "handbrake": {
        "encoder": "x264",
        "quality": 20,
        "audio_bitrate_kbps": 128,
        "audio_mode": "encode",  # encode | copy
        "extra_args": [],
        "extension": ".mkv"
    },
    "handbrake_dvd": {
        "encoder": "x264",
        "quality": 20,
        "width": 1920,
        "height": 1080,
        "extension": ".mkv",
        "extra_args": [],
        "audio_bitrate_kbps": 128,
        "audio_mode": "encode"
    },
    "handbrake_br": {
        "encoder": "x264",
        "quality": 25,
        "width": 3840,
        "height": 2160,
        "extension": ".mkv",
        "extra_args": [],
        "audio_bitrate_kbps": 128,
        "audio_mode": "encode"
    },
    "makemkv_minlength": 1200
}

class ConfigManager:
    def __init__(self, path: Path):
        self.path = path
        self.lock = threading.Lock()

    def read(self) -> Dict[str, Any]:
        with self.lock:
            return load_config(self.path)

    def update(self, data: Dict[str, Any]) -> Dict[str, Any]:
        with self.lock:
            cfg = load_config(self.path)
            for field in ["output_dir", "rip_dir", "final_dir", "max_threads", "rescan_interval", "min_size_mb", "makemkv_minlength", "search_path", "profile"]:
                if field in data and data[field] is not None:
                    cfg[field] = data[field]
            for key in ["handbrake", "handbrake_dvd", "handbrake_br"]:
                if key in data and isinstance(data[key], dict):
                    if key not in cfg or not isinstance(cfg.get(key), dict):
                        cfg[key] = {}
                for k, v in data[key].items():
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
    # ensure handbrake dict exists
    for hb_key in ["handbrake", "handbrake_dvd", "handbrake_br"]:
        if hb_key not in merged or not isinstance(merged.get(hb_key), dict):
            merged[hb_key] = DEFAULT_CONFIG.get(hb_key, {}).copy()
        else:
            hb = DEFAULT_CONFIG.get(hb_key, {}).copy()
            hb.update({k: v for k, v in merged[hb_key].items() if v is not None})
            merged[hb_key] = hb
    if "makemkv_minlength" not in merged:
        merged["makemkv_minlength"] = DEFAULT_CONFIG["makemkv_minlength"]
    return merged


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

import subprocess

def rip_disc(disc_index, output_dir_path, min_length=1800, status_tracker: Optional[StatusTracker] = None):
    """
    Rips a Blu-ray disc using MakeMKV CLI.
    Returns the path to the first output file if successful, or None on failure.
    """
    # return "/mnt/md0/ripped_discs/Interstellar_t00.mkv"
    logger = logging.getLogger(__name__)
    output_dir = output_dir_path.as_posix()
    cmd = [
        "makemkvcon", "mkv", f"disc:{disc_index}", "all", output_dir,
        f"--minlength={min_length}", "--progress=-same"
    ]

    # Check for existing MKVs
    existing_mkvs = sorted(output_dir_path.glob("*.mkv"))
    if existing_mkvs:
        latest = existing_mkvs[-1].resolve()
        print(f"⚠️  Found existing MKV file: {latest}\nSkipping rip.")
        return None

    msg = f"📀 Running: {' '.join(cmd)}"
    print(msg)
    if status_tracker:
        status_tracker.add_event(f"MakeMKV rip started (disc {disc_index})")

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
        return None

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
        return None

    print("✅ MakeMKV completed successfully.")

    # Look for any .mkv files in the output directory
    mkv_files = sorted(output_dir_path.glob("*.mkv"), key=os.path.getmtime)

    if not mkv_files:
        print("⚠️  No MKV files found in output directory.")
        return None

    # Return the most recent or first MKV file path
    first_file = str(mkv_files[-1].resolve())
    print(f"🎬 Output file: {first_file}")
    return first_file

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
    audio_bitrate_kbps = opts.get("audio_bitrate_kbps")
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
        cmd = [
            "HandBrakeCLI",
            "-i", str(input_path),
            "-o", str(output_path),
            "-e", str(encoder),
            "-q", str(quality),
            "--width", str(width),
            "--height", str(height)
            #"-B", str(int(audio_bitrate_kbps))
        ]
        if audio_mode == "copy":
            cmd.extend(["-E", "copy"])
        elif audio_bitrate_kbps:
            try:
                cmd.extend(["-B", str(int(audio_bitrate_kbps))])
            except Exception:
                cmd.extend(["-B", str(audio_bitrate_kbps)])
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

def process_video(video_file: str, config: Dict[str, Any], output_dir: Path, rip_dir: Path, encoder: Encoder, status_tracker: Optional[StatusTracker] = None) -> bool:
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

    hb_opts = config.get(config_str, {})
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

    def probe_source_info(path: Path) -> Optional[str]:
        try:
            if not path.is_file():
                return None
            import json
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

    source_info = probe_source_info(Path(video_file))
    if status_tracker:
        status_tracker.add_event(f"Queued for encode: {src}")
        status_tracker.start(str(src), dest_str, info=source_info)

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
    if is_bluray:
        logging.info("Ripping Blu-ray disc from %s", video_file)
        disc_num = get_disc_number()
        if disc_num is not None:
            minlen = int(config.get("makemkv_minlength", 1800))
            rip_path = rip_disc(disc_num, rip_dir, min_length=minlen, status_tracker=status_tracker)
            if rip_path is None:
                logging.error("Blu-ray ripping failed; skipping encoding for %s", video_file)
                if status_tracker:
                    status_tracker.complete(str(src), False, dest_str, "Blu-ray rip failed")
                return False
        else:
            logging.error("No Blu-ray disc detected; skipping encoding for %s", video_file)
            if status_tracker:
                status_tracker.complete(str(src), False, dest_str, "No Blu-ray detected")
            return False

        video_file = rip_path  # use ripped path for encoding
    if video_file is None:
        if status_tracker:
            status_tracker.complete(str(src), False, dest_str, "No video file to encode")
        return False
    # prefer HandBrakeCLI; if it fails, fall back to encoder.encode_video if available
    use_ffmpeg = str(config_str).startswith("ffmpeg")
    logging.info("Selected profile=%s encoder=%s ext=%s out=%s use_ffmpeg=%s audio_mode=%s audio_kbps=%s",
                 config_str, hb_opts.get("encoder"), extension, out_path, use_ffmpeg,
                 hb_opts.get("audio_mode"), hb_opts.get("audio_bitrate_kbps"))
    success = run_encoder(video_file, str(out_path), hb_opts, use_ffmpeg, status_tracker=status_tracker, job_id=str(src))
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
        except Exception:
            logging.exception("Fallback encoder failed for %s", video_file)
            if status_tracker:
                status_tracker.complete(str(src), False, dest_str, "Fallback encoder failed")
            return False
    else:
        logging.info("Encoded %s -> %s (HandBrakeCLI)", video_file, out_path)
        if status_tracker:
            status_tracker.add_event(f"Encoding complete: {src}")
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
        if is_bluray:
            try:
                # delete ripped file to save space
                rip_fp = Path(video_file)
                rip_fp.unlink()
                logging.info("Deleted ripped Blu-ray file: %s", rip_fp)
            except Exception:
                logging.debug("Failed to delete ripped Blu-ray file: %s", video_file, exc_info=True)
        # Remove source file after a successful encode to avoid re-encoding
        if not is_dvd and not is_bluray:
            try:
                if src.is_file():
                    src.unlink()
                    logging.info("Deleted source file after successful encode: %s", src)
            except Exception:
                logging.debug("Failed to delete source file %s", src, exc_info=True)
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

    logging.info("Starting continuous scanner. search_path=%s output=%s interval=%.1fs",
                 search_path if search_path else "<auto-detect>", output_dir, rescan_interval)

    try:
        while True:
            manual_files = status_tracker.consume_manual_files()
            config = cfg_manager.read()
            rescan_interval = float(config.get("rescan_interval", 30))
            max_threads = int(config.get("max_threads", 4))
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
            if search_path:
                scan_roots = [search_path]
            else:
                base_roots = ["/mnt/input", "/mnt/dvd", "/mnt/bluray", "/mnt/usb"]
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
            video_files.extend(manual_files)
            for f in video_files:
                if status_tracker:
                    status_tracker.add_event(f"Detected new file: {f}")
            if not video_files:
                logging.debug("No candidate video files found on this pass.")
            #for video_file in video_files:               
            with ThreadPoolExecutor(max_workers=max_threads) as ex:
                futures = {ex.submit(process_video, f, config, output_dir, rip_dir, encoder, status_tracker): f for f in video_files}
                for fut in as_completed(futures):
                    src = futures[fut]
                    try:
                        out = fut.result()
                        print(f"✅ {src} → {out}")
                    except Exception as e:
                        print(f"❌ {src}: {e}") 

            time.sleep(rescan_interval)
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
