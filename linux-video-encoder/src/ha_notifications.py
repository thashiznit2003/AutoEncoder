from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any


def _split_service(service_name: str) -> tuple[str, str]:
    text = str(service_name or "").strip()
    if "." in text:
        domain, service = text.split(".", 1)
        return domain.strip(), service.strip()
    return "notify", text


def should_deliver(notification: dict[str, Any], config: dict[str, Any]) -> bool:
    prefs = (config.get("notifications") or {}) if isinstance(config, dict) else {}
    kind = str(notification.get("kind") or "")
    if kind == "job-start":
        return bool(prefs.get("job_start", True))
    if kind == "job-complete":
        return bool(prefs.get("job_complete", True))
    if kind == "job-failed":
        return bool(prefs.get("job_failed", True))
    return False


def send_home_assistant_notification(notification: dict[str, Any], config: dict[str, Any]) -> bool:
    ha = (config.get("home_assistant") or {}) if isinstance(config, dict) else {}
    if not ha.get("enabled"):
        return False
    if not should_deliver(notification, config):
        return False

    base_url = str(ha.get("url") or "").strip().rstrip("/")
    token = str(ha.get("token") or "").strip()
    service_name = str(ha.get("notify_service") or "").strip()
    title_prefix = str(ha.get("title_prefix") or "Linux Video Encoder").strip()
    if not base_url or not token or not service_name:
        return False

    domain, service = _split_service(service_name)
    payload = {
        "title": title_prefix,
        "message": str(notification.get("message") or "").strip() or "Linux Video Encoder notification",
        "data": {
            "tag": "linux-video-encoder",
            "group": "linux-video-encoder",
            "source": notification.get("source") or "",
            "kind": notification.get("kind") or "",
            "level": notification.get("level") or "info",
        },
    }
    req = urllib.request.Request(
        f"{base_url}/api/services/{domain}/{service}",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            _ = resp.read()
        return True
    except urllib.error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8", errors="ignore")
        except Exception:
            body = ""
        logging.warning("Home Assistant notification failed: HTTP %s %s", exc.code, body[:300])
    except Exception:
        logging.exception("Home Assistant notification failed")
    return False
