from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from status_tracker import classify_message


TV_PATTERNS = [
    re.compile(r"\bs\d{1,2}e\d{1,3}\b", re.IGNORECASE),
    re.compile(r"\bseason\s+\d+\b", re.IGNORECASE),
    re.compile(r"\bepisode\s+\d+\b", re.IGNORECASE),
]

EXTRA_PATTERNS = [
    re.compile(r"\b(extra|extras|featurette|deleted scene|trailer|bonus|interview|behind the scenes)\b", re.IGNORECASE),
]


def guess_library_type(path_value: str = "", title: str = "", disc_type: str = "") -> str:
    haystack = " ".join([path_value or "", title or "", disc_type or ""]).replace("_", " ").replace(".", " ")
    if any(pattern.search(haystack) for pattern in EXTRA_PATTERNS):
        return "extras"
    if any(pattern.search(haystack) for pattern in TV_PATTERNS):
        return "tv"
    return "movies"


def apply_name_template(template: str, context: dict[str, Any], fallback: str) -> str:
    text = str(template or "").strip() or fallback
    for key, value in context.items():
        text = text.replace("{" + key + "}", str(value or ""))
    text = re.sub(r"[\\/:*?\"<>|]+", "", text)
    text = re.sub(r"\s+", " ", text).strip(" ._-")
    return text or fallback


def build_name_suggestion(
    path_value: str,
    library_type: str,
    templates: dict[str, str],
    title: str = "",
    disc_label: str = "",
    year: str = "",
    resolution: str = "",
    encoder: str = "",
    disc_type: str = "",
    title_id: str = "",
) -> str:
    path = Path(path_value or "output.mkv")
    source_stem = path.stem
    safe_title = title or disc_label or source_stem
    template = templates.get("movie", "{title}") if library_type == "movies" else templates.get("disc", "{disc_label}")
    context = {
        "title": safe_title,
        "disc_label": disc_label or safe_title,
        "source": source_stem,
        "year": year,
        "resolution": resolution,
        "encoder": encoder,
        "disc_type": disc_type,
        "title_id": title_id,
    }
    return apply_name_template(template, context, safe_title)


def build_job_details(item: dict[str, Any], scope: str, disc_summary: dict[str, Any], destinations: dict[str, str], templates: dict[str, str]) -> dict[str, Any]:
    details = dict(item)
    source = details.get("source") or ""
    destination = details.get("destination") or ""
    rename_to = details.get("rename_to") or ""
    disc_label = disc_summary.get("disc_label") or disc_summary.get("label") or ""
    disc_type = details.get("disc_type") or disc_summary.get("disc_type") or ""
    library_type = guess_library_type(source or destination, rename_to or disc_label, disc_type)
    name_suggestion = build_name_suggestion(
        destination or source,
        library_type,
        templates,
        title=rename_to or disc_label,
        disc_label=disc_label,
        resolution=str(details.get("resolution") or disc_summary.get("resolution") or ""),
        encoder=str(details.get("encoder") or ""),
        disc_type=str(disc_type or ""),
        title_id=str(details.get("title_id") or ""),
    )
    details["scope"] = scope
    details["error_class"] = details.get("error_class") or classify_message(
        details.get("message") or "",
        source,
        destination,
    )
    details["source_exists"] = bool(source and Path(source).exists())
    details["exists"] = bool(destination and Path(destination).exists())
    details["library_type"] = library_type
    details["recommended_destination_root"] = destinations.get(library_type) or ""
    details["name_suggestion"] = name_suggestion
    details["summary"] = {
        "stage": details.get("stage") or "",
        "state": details.get("state") or "",
        "queue_rank": details.get("queue_rank"),
        "queue_held": details.get("queue_held", False),
    }
    return details
