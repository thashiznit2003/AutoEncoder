from pathlib import Path
import json

ALLOWLIST_PATH = Path("/var/lib/autoencoder/state/smb_allowlist.json")


def load_smb_allowlist() -> set[str]:
    ALLOWLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        data = json.loads(ALLOWLIST_PATH.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return set(str(x) for x in data)
    except FileNotFoundError:
        return set()
    except Exception:
        return set()
    return set()


def save_smb_allowlist(entries: set[str]) -> None:
    ALLOWLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        ALLOWLIST_PATH.write_text(json.dumps(sorted(entries)), encoding="utf-8")
    except Exception:
        pass


def enforce_smb_allowlist(staging_dir: str, tracker=None) -> None:
    """
    Remove any files in staging that were not copied by the app and prune stale allowlist entries.
    Allowlist lives in a named volume to survive rebuilds.
    """
    allowlist = load_smb_allowlist()
    staging = Path(staging_dir)
    staging.mkdir(parents=True, exist_ok=True)
    allowed_present = set()
    try:
        for entry in staging.iterdir():
            if not entry.is_file():
                continue
            if entry.name in allowlist:
                allowed_present.add(entry.name)
                continue
            try:
                entry.unlink()
                if tracker:
                    tracker.add_event(f"Removed foreign file from SMB staging: {entry}", level="error")
            except Exception:
                if tracker:
                    tracker.add_event(f"Failed to remove foreign file from SMB staging: {entry}", level="error")
    except FileNotFoundError:
        return
    # Keep allowlist entries even if the file is not present (e.g., mid-copy or awaiting encode).


def remove_from_allowlist(names):
    """
    Remove one or more filenames from the allowlist.
    """
    allowlist = load_smb_allowlist()
    if isinstance(names, str):
        names = [names]
    names = [str(n) for n in names if n]
    updated = allowlist.difference(names)
    if updated != allowlist:
        save_smb_allowlist(updated)
