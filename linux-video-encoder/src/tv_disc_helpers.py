from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _format_code(season: int, episode: int) -> str:
    return f"S{season:02d}E{episode:02d}"


def _sanitize_filename(text: str) -> str:
    value = re.sub(r"[\\/:*?\"<>|]+", "", str(text or "")).strip()
    value = re.sub(r"\s+", " ", value)
    return value.strip(" ._-")


def _extract_audio_bonus(title: Dict[str, Any]) -> int:
    bonus = 0
    streams = title.get("streams") or {}
    for stream in streams.values():
        if str(stream.get("type") or "").lower().startswith("audio"):
            channels = _safe_int(stream.get("channels"), 0)
            if channels >= 6:
                bonus += 4
    return bonus


def _infer_content_kind(title: Dict[str, Any]) -> str:
    duration = float(title.get("duration_seconds") or 0)
    chapters = _safe_int(title.get("chapters"), 0)
    if duration and duration < 300:
        return "menu-or-stinger"
    if duration and duration < 900:
        return "extra"
    if duration and duration > 5400:
        return "feature"
    if chapters and chapters <= 2 and duration < 1800:
        return "extra"
    if 1200 <= duration <= 4200:
        return "episode"
    return "unknown"


def classify_tv_candidates(parsed: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(parsed, dict):
        return {"titles": [], "episode_candidates": [], "extras": []}
    titles = parsed.get("titles") or []
    candidates: List[Dict[str, Any]] = []
    extras: List[Dict[str, Any]] = []
    enriched: List[Dict[str, Any]] = []
    for title in titles:
        item = dict(title)
        duration = float(item.get("duration_seconds") or 0)
        chapters = _safe_int(item.get("chapters"), 0)
        score = 0
        reasons: List[str] = []
        kind = _infer_content_kind(item)
        if 1260 <= duration <= 3600:
            score += 28
            reasons.append("episode-like runtime")
        elif 1080 <= duration <= 4200:
            score += 18
            reasons.append("plausible runtime")
        elif duration > 5400:
            score -= 18
            reasons.append("movie-length runtime")
        elif duration < 900:
            score -= 20
            reasons.append("short runtime")
        else:
            score += 4
            reasons.append("ambiguous runtime")

        if 4 <= chapters <= 14:
            score += 10
            reasons.append("episode-like chapter count")
        elif chapters >= 18:
            score -= 8
            reasons.append("feature-like chapter count")
        elif chapters and chapters <= 2:
            score -= 12
            reasons.append("very few chapters")

        score += _extract_audio_bonus(item)
        if item.get("title_duplicate_group_size", 1) > 1:
            score += 6
            reasons.append("duplicate runtime group")
        if str(item.get("title_confidence") or "") == "high":
            score -= 6
            reasons.append("ranked as main feature")
        if kind == "episode":
            score += 8
        elif kind == "feature":
            score -= 10
        elif kind == "extra":
            score -= 12

        item["content_kind"] = kind
        item["episode_score"] = score
        item["episode_score_reasons"] = reasons
        enriched.append(item)
        if kind == "extra" or score < 0:
            extras.append(item)
        else:
            candidates.append(item)

    candidates.sort(
        key=lambda item: (
            item.get("episode_score", 0),
            -(float(item.get("duration_seconds") or 0) - 2700).__abs__(),
            -_safe_int(item.get("id"), 0),
        ),
        reverse=True,
    )
    for rank, item in enumerate(candidates, start=1):
        item["episode_rank"] = rank
        item["episode_confidence"] = "high" if rank == 1 and item.get("episode_score", 0) >= 34 else ("medium" if item.get("episode_score", 0) >= 22 else "low")
    summary = (parsed.get("summary") or {}).copy()
    summary["episode_candidates"] = [
        {
            "id": item.get("id"),
            "duration": item.get("duration"),
            "duration_seconds": item.get("duration_seconds"),
            "chapters": item.get("chapters"),
            "playlist": item.get("playlist"),
            "episode_score": item.get("episode_score"),
            "episode_confidence": item.get("episode_confidence"),
            "content_kind": item.get("content_kind"),
            "reasons": list(item.get("episode_score_reasons") or [])[:3],
        }
        for item in candidates[:12]
    ]
    return {"titles": enriched, "episode_candidates": candidates, "extras": extras, "summary": summary}


def _tvmaze_get_json(url: str, timeout: int = 10) -> Any:
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "linux-video-encoder/1"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def tvmaze_search(query: str) -> List[Dict[str, Any]]:
    q = str(query or "").strip()
    if not q:
        return []
    url = "https://api.tvmaze.com/search/shows?q=" + urllib.parse.quote(q)
    payload = _tvmaze_get_json(url)
    results = []
    for item in payload or []:
        show = item.get("show") or {}
        results.append(
            {
                "id": show.get("id"),
                "name": show.get("name") or "",
                "premiered": show.get("premiered") or "",
                "status": show.get("status") or "",
                "summary": re.sub(r"<[^>]+>", "", str(show.get("summary") or "")).strip(),
            }
        )
    return results


def tvmaze_episodes(show_id: str | int) -> List[Dict[str, Any]]:
    sid = str(show_id or "").strip()
    if not sid:
        return []
    url = f"https://api.tvmaze.com/shows/{urllib.parse.quote(sid)}/episodes"
    payload = _tvmaze_get_json(url)
    episodes = []
    for item in payload or []:
        episodes.append(
            {
                "id": item.get("id"),
                "name": item.get("name") or "",
                "season": _safe_int(item.get("season"), 0),
                "number": _safe_int(item.get("number"), 0),
                "runtime": _safe_int(item.get("runtime"), 0),
                "airdate": item.get("airdate") or "",
            }
        )
    return episodes


def select_episode_candidates(parsed: Dict[str, Any], count: int = 4, selected_titles: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    classified = classify_tv_candidates(parsed)
    candidates = classified["episode_candidates"]
    selected_set = {str(item).strip() for item in (selected_titles or []) if str(item).strip()}
    if selected_set:
        chosen = [item for item in candidates if str(item.get("id")) in selected_set]
        if chosen:
            return sorted(chosen, key=lambda item: _safe_int(item.get("id"), 0))
    top = candidates[: max(1, count)]
    return sorted(top, key=lambda item: _safe_int(item.get("id"), 0))


def build_episode_filename(show_title: str, season: int, episode: int, episode_title: str = "") -> str:
    code = _format_code(season, episode)
    title = _sanitize_filename(show_title) or "Show"
    ep_name = _sanitize_filename(episode_title)
    if ep_name:
        return f"{title} - {code} - {ep_name}"
    return f"{title} - {code}"


def build_episode_plan(
    parsed: Dict[str, Any],
    show_title: str,
    season_number: int,
    episode_start: int,
    selected_titles: Optional[List[str]] = None,
    metadata_episodes: Optional[List[Dict[str, Any]]] = None,
    count: int = 4,
    existing_plan: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    selected = select_episode_candidates(parsed, count=count, selected_titles=selected_titles)
    episode_cursor = max(1, _safe_int(episode_start, 1))
    existing_by_title = {}
    for item in (existing_plan or {}).get("planned_titles") or []:
        title_id = str(item.get("title_id") or "").strip()
        if title_id:
            existing_by_title[title_id] = item
    season = max(1, _safe_int(season_number, 1))
    metadata_by_code = {}
    for episode in metadata_episodes or []:
        metadata_by_code[_format_code(_safe_int(episode.get("season"), 0), _safe_int(episode.get("number"), 0))] = episode
    planned = []
    warnings = []
    for title in selected:
        code = _format_code(season, episode_cursor)
        episode_meta = metadata_by_code.get(code) or {}
        title_id = str(title.get("id"))
        current = existing_by_title.get(title_id) or {}
        runtime_seconds = _safe_int(title.get("duration_seconds"), 0)
        meta_runtime = _safe_int(episode_meta.get("runtime"), 0) * 60
        confidence = str(title.get("episode_confidence") or "low")
        if meta_runtime and runtime_seconds:
            delta = abs(runtime_seconds - meta_runtime)
            if delta <= 180:
                confidence = "high"
            elif delta <= 420 and confidence == "low":
                confidence = "medium"
        planned.append(
            {
                "title_id": title_id,
                "playlist": str(title.get("playlist") or ""),
                "season": season,
                "episode": episode_cursor,
                "code": code,
                "episode_title": str(current.get("episode_title") or episode_meta.get("name") or "").strip(),
                "filename": str(current.get("filename") or build_episode_filename(show_title, season, episode_cursor, episode_meta.get("name") or "")).strip(),
                "confidence": confidence,
                "runtime_seconds": runtime_seconds,
                "runtime": str(title.get("duration") or ""),
                "menu_label": str(current.get("menu_label") or "").strip(),
                "notes": str(current.get("notes") or "").strip(),
                "reasons": list(title.get("episode_score_reasons") or [])[:3],
                "episode_score": title.get("episode_score"),
            }
        )
        episode_cursor += 1
    if metadata_episodes and len(planned) > len(metadata_episodes):
        warnings.append("Metadata returned fewer episodes than the number of selected titles.")
    if not planned:
        warnings.append("No episode-like titles were available to plan.")
    return {
        "show_title": str(show_title or "").strip(),
        "season_number": season,
        "episode_start": max(1, _safe_int(episode_start, 1)),
        "selected_titles": [str(item.get("title_id") or item.get("id")) for item in planned],
        "planned_titles": planned,
        "warnings": warnings,
    }
