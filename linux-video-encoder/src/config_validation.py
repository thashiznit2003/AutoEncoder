from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Iterable, Tuple


def _csv_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    if isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray, dict)):
        out = []
        for item in value:
            text = str(item).strip()
            if text:
                out.append(text)
        return out
    return []


def _bounded_int(value: Any, default: int, minimum: int | None = None, maximum: int | None = None) -> int:
    try:
        parsed = int(value)
    except Exception:
        parsed = default
    if minimum is not None:
        parsed = max(minimum, parsed)
    if maximum is not None:
        parsed = min(maximum, parsed)
    return parsed


def _bounded_float(value: Any, default: float | None, minimum: float | None = None, maximum: float | None = None) -> float | None:
    if value in ("", None):
        return default
    try:
        parsed = float(value)
    except Exception:
        return default
    if minimum is not None:
        parsed = max(minimum, parsed)
    if maximum is not None:
        parsed = min(maximum, parsed)
    return parsed


def sanitize_template(value: Any, default: str) -> str:
    text = str(value or "").strip() or default
    allowed = ["{title}", "{disc_label}", "{source}", "{year}", "{resolution}", "{encoder}", "{disc_type}", "{title_id}"]
    if not any(token in text for token in allowed):
        text = default
    return text[:160]


def validate_final_destinations(value: Any) -> Dict[str, str]:
    src = value if isinstance(value, dict) else {}
    return {
        "movies": str(src.get("movies") or "").strip(),
        "tv": str(src.get("tv") or "").strip(),
        "extras": str(src.get("extras") or "").strip(),
    }


def validate_notifications(value: Any) -> Dict[str, bool]:
    src = value if isinstance(value, dict) else {}
    return {
        "browser": bool(src.get("browser", True)),
        "job_start": bool(src.get("job_start", True)),
        "job_complete": bool(src.get("job_complete", True)),
        "job_failed": bool(src.get("job_failed", True)),
    }


def validate_home_assistant(value: Any) -> Dict[str, Any]:
    src = value if isinstance(value, dict) else {}
    return {
        "enabled": bool(src.get("enabled", False)),
        "url": str(src.get("url") or "").strip().rstrip("/"),
        "token": str(src.get("token") or "").strip(),
        "notify_service": str(src.get("notify_service") or "").strip(),
        "title_prefix": str(src.get("title_prefix") or "Linux Video Encoder").strip()[:120] or "Linux Video Encoder",
    }


def validate_disc_title_preferences(value: Any) -> Dict[str, Dict[str, list[str]]]:
    src = value if isinstance(value, dict) else {}
    out: Dict[str, Dict[str, list[str]]] = {}
    for disc_key, prefs in src.items():
        if not isinstance(prefs, dict):
            continue
        out[str(disc_key)] = {
            "prefer_titles": _csv_list(prefs.get("prefer_titles")),
            "blocked_titles": _csv_list(prefs.get("blocked_titles")),
        }
    return out


def normalize_config(cfg: Dict[str, Any], defaults: Dict[str, Any]) -> Dict[str, Any]:
    merged = deepcopy(defaults)
    merged.update({k: v for k, v in (cfg or {}).items() if v is not None})

    merged["output_dir"] = str(merged["output_dir"])
    merged["rip_dir"] = str(merged["rip_dir"])
    merged["final_dir"] = str(merged.get("final_dir") or "")
    merged["smb_staging_dir"] = str(merged.get("smb_staging_dir") or defaults["smb_staging_dir"])
    merged["usb_staging_dir"] = str(merged.get("usb_staging_dir") or defaults["usb_staging_dir"])

    merged["max_threads"] = _bounded_int(merged.get("max_threads"), defaults["max_threads"], minimum=1, maximum=32)
    merged["rescan_interval"] = _bounded_int(merged.get("rescan_interval"), defaults["rescan_interval"], minimum=1, maximum=600)
    merged["min_size_mb"] = _bounded_int(merged.get("min_size_mb"), defaults["min_size_mb"], minimum=1, maximum=102400)
    merged["makemkv_minlength"] = _bounded_int(merged.get("makemkv_minlength"), defaults["makemkv_minlength"], minimum=60, maximum=43200)

    merged["auth_user"] = str(merged.get("auth_user") or defaults["auth_user"])
    merged["auth_password"] = str(merged.get("auth_password") or defaults["auth_password"])

    extra_auth_users = merged.get("auth_additional_users", [])
    if not isinstance(extra_auth_users, list):
        extra_auth_users = []
    normalized_extra_auth_users = []
    for entry in extra_auth_users:
        if not isinstance(entry, dict):
            continue
        username = str(entry.get("username") or "").strip()
        password = str(entry.get("password") or "")
        if username and password:
            normalized_extra_auth_users.append({"username": username, "password": password})
    merged["auth_additional_users"] = normalized_extra_auth_users

    for hb_key in ["handbrake", "handbrake_dvd", "handbrake_br"]:
        hb = deepcopy(defaults.get(hb_key, {}))
        if isinstance(merged.get(hb_key), dict):
            hb.update({k: v for k, v in merged[hb_key].items() if v is not None})
        hb["quality"] = _bounded_int(hb.get("quality"), defaults[hb_key]["quality"], minimum=12, maximum=40)
        hb["video_bitrate_kbps"] = _bounded_int(hb.get("video_bitrate_kbps"), 0, minimum=0, maximum=200000) or None
        hb["two_pass"] = bool(hb.get("two_pass"))
        hb["audio_offset_ms"] = _bounded_int(hb.get("audio_offset_ms"), 0, minimum=-5000, maximum=5000)
        hb["audio_bitrate_kbps"] = _bounded_int(hb.get("audio_bitrate_kbps"), 128, minimum=32, maximum=1536)
        hb["audio_mode"] = str(hb.get("audio_mode") or "encode")
        hb["audio_encoder"] = str(hb.get("audio_encoder") or "av_aac")
        hb["audio_mixdown"] = str(hb.get("audio_mixdown") or "")
        hb["audio_drc"] = _bounded_float(hb.get("audio_drc"), None, minimum=0, maximum=4)
        hb["audio_gain"] = _bounded_float(hb.get("audio_gain"), None, minimum=-20, maximum=20)
        hb["audio_samplerate"] = str(hb.get("audio_samplerate") or "")
        hb["audio_lang_list"] = _csv_list(hb.get("audio_lang_list"))
        hb["audio_track_list"] = str(hb.get("audio_track_list") or "")
        hb["audio_all"] = bool(hb.get("audio_all"))
        hb["subtitle_mode"] = str(hb.get("subtitle_mode") or "none")
        hb["extension"] = str(hb.get("extension") or ".mkv")
        merged[hb_key] = hb

    for key in ["makemkv_titles", "makemkv_audio_langs", "makemkv_subtitle_langs", "makemkv_preferred_audio_langs", "makemkv_preferred_subtitle_langs"]:
        merged[key] = _csv_list(merged.get(key))

    merged["makemkv_keep_ripped"] = bool(merged.get("makemkv_keep_ripped"))
    merged["makemkv_exclude_commentary"] = bool(merged.get("makemkv_exclude_commentary"))
    merged["makemkv_prefer_surround"] = bool(merged.get("makemkv_prefer_surround"))
    merged["makemkv_auto_rip"] = bool(merged.get("makemkv_auto_rip"))
    merged["low_bitrate_auto_proceed"] = bool(merged.get("low_bitrate_auto_proceed"))
    merged["low_bitrate_auto_skip"] = bool(merged.get("low_bitrate_auto_skip"))
    merged["advanced_mode"] = bool(merged.get("advanced_mode"))
    merged["queue_pause_after_current"] = bool(merged.get("queue_pause_after_current"))

    merged["naming_template_movie"] = sanitize_template(merged.get("naming_template_movie"), defaults["naming_template_movie"])
    merged["naming_template_disc"] = sanitize_template(merged.get("naming_template_disc"), defaults["naming_template_disc"])
    merged["final_destinations"] = validate_final_destinations(merged.get("final_destinations"))
    merged["notifications"] = validate_notifications(merged.get("notifications"))
    merged["home_assistant"] = validate_home_assistant(merged.get("home_assistant"))
    merged["disc_title_preferences"] = validate_disc_title_preferences(merged.get("disc_title_preferences"))

    if not isinstance(merged.get("handbrake_presets"), list):
        merged["handbrake_presets"] = []
    if not isinstance(merged.get("audio_subtitle_presets"), dict):
        merged["audio_subtitle_presets"] = deepcopy(defaults["audio_subtitle_presets"])
    if not isinstance(merged.get("disc_profile_presets"), dict):
        merged["disc_profile_presets"] = deepcopy(defaults["disc_profile_presets"])
    return merged


def validate_update_payload(data: Dict[str, Any]) -> Tuple[Dict[str, Any], list[str]]:
    payload = deepcopy(data or {})
    warnings: list[str] = []
    if "rescan_interval" in payload:
        before = payload["rescan_interval"]
        payload["rescan_interval"] = _bounded_int(before, 30, minimum=1, maximum=600)
        if payload["rescan_interval"] != before:
            warnings.append("rescan_interval was clamped into the supported range.")
    if "makemkv_minlength" in payload:
        before = payload["makemkv_minlength"]
        payload["makemkv_minlength"] = _bounded_int(before, 1200, minimum=60, maximum=43200)
        if payload["makemkv_minlength"] != before:
            warnings.append("makemkv_minlength was clamped into the supported range.")
    if "naming_template_movie" in payload:
        payload["naming_template_movie"] = sanitize_template(payload["naming_template_movie"], "{title}")
    if "naming_template_disc" in payload:
        payload["naming_template_disc"] = sanitize_template(payload["naming_template_disc"], "{disc_label}")
    if "final_destinations" in payload:
        payload["final_destinations"] = validate_final_destinations(payload["final_destinations"])
    if "notifications" in payload:
        payload["notifications"] = validate_notifications(payload["notifications"])
    if "home_assistant" in payload:
        payload["home_assistant"] = validate_home_assistant(payload["home_assistant"])
    if "disc_title_preferences" in payload:
        payload["disc_title_preferences"] = validate_disc_title_preferences(payload["disc_title_preferences"])
    return payload, warnings
