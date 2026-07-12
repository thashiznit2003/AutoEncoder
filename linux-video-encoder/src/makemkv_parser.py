import re
from typing import Any, Dict, List, Optional


DEFAULT_SCORE_PREFERENCES: Dict[str, Any] = {
    "preferred_audio_langs": ["eng"],
    "preferred_subtitle_langs": ["eng"],
    "prefer_surround": True,
    "exclude_commentary": False,
}


def _parse_duration_to_seconds(val: str) -> Optional[float]:
    """Parse duration strings like 1:23:45 or PT1H23M45S into seconds."""
    if not val:
        return None
    v = val.strip().upper()
    iso = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", v)
    if iso:
        h = int(iso.group(1) or 0)
        m = int(iso.group(2) or 0)
        s = float(iso.group(3) or 0)
        return h * 3600 + m * 60 + s
    if ":" in v:
        try:
            parts = [float(p) for p in v.split(":")]
            sec = 0.0
            for p in parts:
                sec = sec * 60 + p
            return sec
        except Exception:
            return None
    try:
        return float(v)
    except Exception:
        return None


def _format_duration(seconds: Optional[float]) -> Optional[str]:
    if seconds is None:
        return None
    try:
        sec = int(round(float(seconds)))
    except Exception:
        return None
    h = sec // 3600
    m = (sec % 3600) // 60
    s = sec % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def _dedup(seq: List[str]) -> List[str]:
    seen = set()
    out = []
    for item in seq:
        if not item:
            continue
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _normalize_langs(values: Any) -> List[str]:
    out: List[str] = []
    for value in values or []:
        text = str(value or "").strip().lower()
        if not text:
            continue
        out.append(text[:3])
    return _dedup(out)


def _stream_list(title: Dict[str, Any], prefix: str) -> List[Dict[str, Any]]:
    streams = title.get("streams") or {}
    return [
        stream
        for stream in streams.values()
        if str(stream.get("type", "")).lower().startswith(prefix)
    ]


def _stream_lang(stream: Dict[str, Any]) -> str:
    return str(stream.get("lang_code") or stream.get("lang_name") or "").strip().lower()[:3]


def _commentary_present(title: Dict[str, Any]) -> bool:
    haystacks = []
    haystacks.extend(title.get("audio_tracks") or [])
    haystacks.extend(title.get("subtitle_tracks") or [])
    source = title.get("source")
    if source:
        haystacks.append(source)
    for item in haystacks:
        low = str(item or "").lower()
        if "commentary" in low or "director" in low and "commentary" in low:
            return True
    return False


def _duplicate_signature(title: Dict[str, Any]) -> tuple:
    dur = int(round(float(title.get("duration_seconds") or 0)))
    video_streams = _stream_list(title, "video")
    resolution = ""
    aspect = ""
    if video_streams:
        resolution = str(video_streams[0].get("resolution") or "")
        aspect = str(video_streams[0].get("aspect") or "")
    return (
        dur,
        int(title.get("chapters") or 0),
        resolution,
        aspect,
    )


def apply_title_scores(parsed: Dict[str, Any], preferences: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if not isinstance(parsed, dict):
        return parsed
    titles = parsed.get("titles") or []
    if not titles:
        return parsed

    prefs = dict(DEFAULT_SCORE_PREFERENCES)
    if preferences:
        prefs.update({k: v for k, v in preferences.items() if v is not None})
    pref_audio = _normalize_langs(prefs.get("preferred_audio_langs") or [])
    pref_subs = _normalize_langs(prefs.get("preferred_subtitle_langs") or [])
    prefer_surround = bool(prefs.get("prefer_surround", True))
    exclude_commentary = bool(prefs.get("exclude_commentary", False))

    durations = [float(t.get("duration_seconds") or 0) for t in titles]
    max_duration = max(durations) if durations else 0.0
    duplicate_counts: Dict[tuple, int] = {}
    for title in titles:
        sig = _duplicate_signature(title)
        duplicate_counts[sig] = duplicate_counts.get(sig, 0) + 1

    for title in titles:
        reasons: List[str] = []
        score = 0
        dur = float(title.get("duration_seconds") or 0)
        chapters = int(title.get("chapters") or 0)
        audio_streams = _stream_list(title, "audio")
        video_streams = _stream_list(title, "video")
        subtitle_streams = _stream_list(title, "subtitle")
        audio_langs = _dedup(
            _normalize_langs(title.get("audio_langs") or [])
            + [_stream_lang(s) for s in audio_streams if _stream_lang(s)]
        )
        subtitle_langs = _dedup(
            _normalize_langs(title.get("subtitle_langs") or [])
            + [_stream_lang(s) for s in subtitle_streams if _stream_lang(s)]
        )
        surround_streams = [s for s in audio_streams if str(s.get("channels") or "").isdigit() and int(s.get("channels")) >= 6]
        pref_audio_match = any(lang in pref_audio for lang in audio_langs) if pref_audio else bool(audio_langs)
        pref_sub_match = any(lang in pref_subs for lang in subtitle_langs) if pref_subs else bool(subtitle_langs)
        commentary = _commentary_present(title)
        duplicate_size = duplicate_counts.get(_duplicate_signature(title), 1)

        if max_duration > 0 and dur >= max_duration * 0.95:
            score += 40
            reasons.append("near-longest runtime")
        elif max_duration > 0 and dur >= max_duration * 0.80:
            score += 24
            reasons.append("long runtime")
        elif dur >= 1800:
            score += 12
            reasons.append("feature-length runtime")
        elif dur < 900:
            score -= 28
            reasons.append("short runtime")
        else:
            score -= 8
            reasons.append("middling runtime")

        if chapters >= 18:
            score += 14
            reasons.append("many chapters")
        elif chapters >= 10:
            score += 8
            reasons.append("movie-like chapter count")
        elif chapters and chapters <= 4:
            score -= 8
            reasons.append("few chapters")

        if pref_audio_match:
            score += 18
            reasons.append("preferred audio language")
        elif pref_audio:
            score -= 10
            reasons.append("missing preferred audio")

        if pref_sub_match:
            score += 6
            reasons.append("preferred subtitle language")

        if surround_streams:
            score += 10 if prefer_surround else 6
            reasons.append("surround audio present")
        elif audio_streams and prefer_surround:
            score -= 4
            reasons.append("no surround audio")

        if commentary:
            score -= 12
            reasons.append("commentary markers present")
            if exclude_commentary:
                score -= 10
                reasons.append("commentary deprioritized")

        if duplicate_size > 1:
            if pref_audio_match:
                score += 8
                reasons.append("best match among duplicate-length titles")
            else:
                score -= 4
                reasons.append("duplicate-length title variant")

        if video_streams:
            resolution = str(video_streams[0].get("resolution") or "")
            aspect = str(video_streams[0].get("aspect") or "")
            if resolution.startswith("1920x1080") or resolution.startswith("3840x2160"):
                score += 4
                reasons.append("full feature resolution")
            if aspect == "16:9":
                score += 2
                reasons.append("standard feature aspect")

        title["title_score"] = score
        title["title_score_reasons"] = reasons
        title["title_duplicate_group_size"] = duplicate_size

    ranked = sorted(
        titles,
        key=lambda t: (
            t.get("title_score", 0),
            t.get("duration_seconds", 0) or 0,
            t.get("chapters", 0) or 0,
        ),
        reverse=True,
    )
    top_score = ranked[0].get("title_score", 0)
    second_score = ranked[1].get("title_score", top_score) if len(ranked) > 1 else top_score
    for idx, title in enumerate(ranked, start=1):
        title["title_rank"] = idx
        gap = top_score - (ranked[1].get("title_score", top_score) if len(ranked) > 1 else top_score)
        if idx == 1 and gap >= 15:
            confidence = "high"
        elif idx == 1 and gap >= 8:
            confidence = "medium"
        elif idx == 1:
            confidence = "low"
        else:
            confidence = "alternate"
        title["title_confidence"] = confidence

    parsed["titles"] = ranked
    summary = parsed.setdefault("summary", {})
    best = ranked[0]
    summary["main_feature"] = {
        "id": best.get("id"),
        "playlist": best.get("playlist"),
        "duration": best.get("duration"),
        "chapters": best.get("chapters"),
        "score": best.get("title_score"),
        "confidence": best.get("title_confidence"),
        "reasons": best.get("title_score_reasons", [])[:3],
    }
    summary["top_candidates"] = [
        {
            "id": t.get("id"),
            "playlist": t.get("playlist"),
            "duration": t.get("duration"),
            "chapters": t.get("chapters"),
            "score": t.get("title_score"),
            "confidence": t.get("title_confidence"),
            "reasons": t.get("title_score_reasons", [])[:3],
        }
        for t in ranked[:3]
    ]
    summary["title_count"] = len(ranked)
    return parsed


def format_disc_overview(parsed: Dict[str, Any]) -> str:
    """Build a human-friendly overview string from parsed MakeMKV info."""
    if not parsed:
        return ""
    lines: List[str] = []
    summary = parsed.get("summary") or {}
    head_parts = []
    if summary.get("disc_label"):
        head_parts.append(f"Label: {summary['disc_label']}")
    if summary.get("drive"):
        head_parts.append(f"Drive: {summary['drive']}")
    if summary.get("titles_detected") or summary.get("title_count"):
        head_parts.append(f"Titles: {summary.get('titles_detected') or summary.get('title_count')}")
    if summary.get("main_feature"):
        mf = summary["main_feature"]
        mf_parts = []
        if mf.get("id") is not None:
            mf_parts.append(f"id {mf['id']}")
        if mf.get("playlist"):
            mf_parts.append(mf["playlist"])
        if mf.get("duration"):
            mf_parts.append(mf["duration"])
        if mf.get("chapters") is not None:
            mf_parts.append(f"{mf['chapters']} chapters")
        if mf_parts:
            head_parts.append("Main: " + " | ".join(mf_parts))
    if head_parts:
        lines.append(" | ".join(head_parts))
    titles = parsed.get("titles") or []
    selected = titles[:3]

    for t in selected:
        parts = []
        label = f"Title {t.get('id', '?')}"
        if t.get("playlist"):
            label += f" ({t['playlist']})"
        parts.append(label)
        if t.get("title_score") is not None:
            parts.append(f"score {t.get('title_score')}")
        if t.get("title_confidence"):
            parts.append(t.get("title_confidence"))
        if t.get("duration"):
            parts.append(t["duration"])
        if t.get("chapters") is not None:
            parts.append(f"{t['chapters']} chapters")
        # Video summary
        video_str = None
        streams = t.get("streams") or {}
        video_streams = [s for s in streams.values() if str(s.get("type", "")).lower().startswith("video")]
        if video_streams:
            v = video_streams[0]
            bits = []
            if v.get("codec"):
                bits.append(v["codec"])
            if v.get("resolution"):
                bits.append(v["resolution"])
            if v.get("framerate"):
                bits.append(v["framerate"])
            if bits:
                video_str = "video: " + " ".join(bits)
        if not video_streams and t.get("video"):
            video_str = "video: " + t["video"]
        if video_str:
            parts.append(video_str)
        # Audio summary
        audio_streams = [s for s in streams.values() if str(s.get("type", "")).lower().startswith("audio")]
        if audio_streams:
            agg = {}
            for a in audio_streams:
                lang = a.get("lang_code") or a.get("lang_name") or "und"
                codec = a.get("codec") or ""
                ch = a.get("channels") or ""
                key = (lang, codec, ch)
                agg[key] = agg.get(key, 0) + 1
            audio_bits = []
            for (lang, codec, ch), count in sorted(agg.items(), key=lambda kv: kv[1], reverse=True):
                desc = lang
                if codec:
                    desc += f" {codec}"
                if ch:
                    desc += f" {ch}"
                if count > 1:
                    desc += f" x{count}"
                audio_bits.append(desc)
            if audio_bits:
                audio_short = ", ".join(audio_bits[:4])
                if len(audio_bits) > 4:
                    audio_short += " …"
                parts.append("audio: " + audio_short)
        elif t.get("audio_tracks"):
            audio_list = t["audio_tracks"]
            suffix = "…" if len(audio_list) > 2 else ""
            parts.append("audio: " + "; ".join(audio_list[:2]) + suffix)
        # Subtitle summary
        subtitle_streams = [s for s in streams.values() if str(s.get("type", "")).lower().startswith("subtitle")]
        if subtitle_streams:
            langs = []
            for s in subtitle_streams:
                langs.append(s.get("lang_code") or s.get("lang_name") or "und")
            langs = _dedup(langs)
            sub_short = ", ".join(langs[:6])
            if len(langs) > 6:
                sub_short += " …"
            parts.append("subs: " + sub_short)
        elif t.get("subtitle_tracks"):
            sub_list = t["subtitle_tracks"]
            suffix = "…" if len(sub_list) > 2 else ""
            parts.append("subs: " + "; ".join(sub_list[:2]) + suffix)
        reasons = t.get("title_score_reasons") or []
        if reasons:
            parts.append("why: " + ", ".join(reasons[:3]))
        lines.append(" | ".join(parts))
    return "\n".join([ln for ln in lines if ln])


def parse_makemkv_info_output(raw: str, preferences: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Parse makemkvcon info output into structured data while keeping raw text.
    Returns a dict with keys: raw, titles, summary, formatted.
    """
    parsed: Dict[str, Any] = {"raw": raw or ""}
    if not raw:
        return parsed
    titles: Dict[int, Dict[str, Any]] = {}
    msg_titles: Dict[str, Dict[str, Any]] = {}
    summary: Dict[str, Any] = {}
    drv_re = re.compile(r'^DRV:\d+,\d+,\d+,\d+,"([^"]*)"(?:,"([^"]*)")?')
    msg_title_re = re.compile(
        r"Title #(?P<playlist>\d+)[^\n]*length (?P<length>[0-9:]+)(?:[^\d]+(?P<chapters>\d+) chapters)?",
        re.IGNORECASE,
    )
    msg_added_re = re.compile(
        r"Title #(?P<id>\d+)\s+was added\s*\\((?P<cells>\d+)\\s*cell\\(s\\),\\s*(?P<length>[0-9:]+)\\)",
        re.IGNORECASE,
    )

    lines = [ln for ln in raw.splitlines() if ln]
    error_lines = [ln for ln in lines if ln.lower().startswith("error:")]
    if error_lines:
        parsed["error"] = "; ".join(error_lines)
    # filter out error lines from parsing
    lines = [ln for ln in lines if not ln.lower().startswith("error:")]

    def ensure_title(idx: int) -> Dict[str, Any]:
        if idx not in titles:
            titles[idx] = {
                "id": idx,
                "tinfo": [],
                "sinfo": [],
                "audio_tracks": [],
                "subtitle_tracks": [],
                "audio_langs": [],
                "subtitle_langs": [],
                "streams": {},
            }
        return titles[idx]

    for line in lines:
        ln = line.strip()
        if not ln:
            continue
        drv_match = drv_re.match(ln)
        if drv_match:
            drive = drv_match.group(1) or ""
            if drive:
                summary.setdefault("drive", drive)
            label = drv_match.group(2) or ""
            if label:
                summary.setdefault("disc_label", label)
        if "was added as title" in ln:
            summary["titles_detected"] = summary.get("titles_detected", 0) + 1
        msg_match = msg_title_re.search(ln)
        if msg_match:
            playlist = msg_match.group("playlist") or ""
            msg_entry = msg_titles.setdefault(playlist.lstrip("0") or playlist, {})
            length_val = msg_match.group("length")
            dur_sec = _parse_duration_to_seconds(length_val)
            if dur_sec:
                msg_entry["duration_seconds"] = dur_sec
                msg_entry["duration"] = _format_duration(dur_sec)
            chapters_val = msg_match.group("chapters")
            if chapters_val and chapters_val.isdigit():
                msg_entry["chapters"] = int(chapters_val)
        msg_added_match = msg_added_re.search(ln)
        if msg_added_match:
            try:
                title_id = int(msg_added_match.group("id"))
            except Exception:
                title_id = None
            if title_id is not None:
                entry = ensure_title(title_id)
                length_val = msg_added_match.group("length")
                dur_sec = _parse_duration_to_seconds(length_val)
                if dur_sec:
                    entry.setdefault("duration_seconds", dur_sec)
                    entry.setdefault("duration", _format_duration(dur_sec))
                cells_val = msg_added_match.group("cells")
                if cells_val and cells_val.isdigit():
                    cells = int(cells_val)
                    entry.setdefault("cells", cells)
                    if "chapters" not in entry:
                        entry["chapters"] = cells
        if ln.startswith("TINFO:"):
            try:
                import csv
                rest = ln.split(":", 1)[1]
                tokens = next(csv.reader([rest]))
                if len(tokens) < 3:
                    continue
                title_id = int(tokens[0])
                info_id = int(tokens[1])
                value = (tokens[-1] or "").strip()
                entry = ensure_title(title_id)
                entry["tinfo"].append(ln)
                if info_id == 2 and value:
                    entry["source"] = value
                    pl_match = re.search(r"(\\d{1,5})\\.mpls", value, re.IGNORECASE)
                    if not pl_match:
                        pl_match = re.search(r"mpls[^0-9]*(\\d{1,5})", value, re.IGNORECASE)
                    if pl_match:
                        entry["playlist"] = pl_match.group(1).lstrip("0") or pl_match.group(1)
                if info_id == 8:
                    if value.isdigit():
                        entry["chapters"] = int(value)
                    else:
                        dur = _parse_duration_to_seconds(value)
                        if dur:
                            entry["duration_seconds"] = dur
                if info_id == 9:
                    dur = _parse_duration_to_seconds(value)
                    if dur:
                        entry["duration_seconds"] = dur
                if info_id == 10 and value:
                    entry["video"] = value
                if info_id == 11 and value:
                    entry["audio_langs"].append(value)
                if info_id == 12 and value:
                    entry["audio_tracks"].append(value)
                if info_id == 13 and value:
                    entry["subtitle_langs"].append(value)
            except Exception:
                continue
            continue
        if ln.startswith("SINFO:"):
            try:
                import csv
                rest = ln.split(":", 1)[1]
                tokens = next(csv.reader([rest]))
                if len(tokens) < 5:
                    continue
                title_id = int(tokens[0])
                stream_id = int(tokens[1])
                field_id = int(tokens[2])
                value = (tokens[4] or "").strip()
                entry = ensure_title(title_id)
                entry["sinfo"].append(ln)
                streams = entry.setdefault("streams", {})
                stream = streams.setdefault(stream_id, {})
                if field_id == 1:
                    stream["type"] = value
                elif field_id == 3:
                    stream["lang_code"] = value
                elif field_id == 4:
                    stream["lang_name"] = value
                elif field_id in (5, 6, 7):
                    stream.setdefault("codec", value)
                elif field_id == 14:
                    stream["channels"] = value
                elif field_id == 19:
                    stream["resolution"] = value
                elif field_id == 20:
                    stream["aspect"] = value
                elif field_id == 21:
                    stream["framerate"] = value
                lower = value.lower()
                def _after_colon(val: str) -> str:
                    if ":" in val:
                        return val.split(":", 1)[1].strip() or val
                    return val
                if lower.startswith("audio:"):
                    entry["audio_tracks"].append(_after_colon(value))
                elif lower.startswith("subtitle"):
                    entry["subtitle_tracks"].append(_after_colon(value))
                elif lower.startswith("video"):
                    entry.setdefault("video", _after_colon(value))
            except Exception:
                continue

    # Merge inferred data and clean up lists
    titles_out: List[Dict[str, Any]] = []
    for idx in sorted(titles.keys()):
        entry = titles[idx]
        playlist = entry.get("playlist")
        if not playlist and entry.get("source"):
            pl_match = re.search(r"(\\d{1,5})\\.mpls", entry["source"], re.IGNORECASE)
            if not pl_match:
                pl_match = re.search(r"mpls[^0-9]*(\\d{1,5})", entry["source"], re.IGNORECASE)
            if pl_match:
                entry["playlist"] = pl_match.group(1).lstrip("0") or pl_match.group(1)
                playlist = entry["playlist"]
        msg_entry = None
        if playlist:
            msg_entry = msg_titles.get(playlist.lstrip("0")) or msg_titles.get(playlist)
        if msg_entry:
            if "duration_seconds" in msg_entry and "duration_seconds" not in entry:
                entry["duration_seconds"] = msg_entry["duration_seconds"]
            if "chapters" in msg_entry and "chapters" not in entry:
                entry["chapters"] = msg_entry["chapters"]
        if "duration_seconds" in entry:
            entry["duration"] = _format_duration(entry.get("duration_seconds"))
        entry["audio_tracks"] = _dedup(entry.get("audio_tracks", []))
        entry["subtitle_tracks"] = _dedup(entry.get("subtitle_tracks", []))
        entry["audio_langs"] = _dedup(entry.get("audio_langs", []))
        entry["subtitle_langs"] = _dedup(entry.get("subtitle_langs", []))
        titles_out.append(entry)

    parsed["titles"] = titles_out
    if titles_out and "titles_detected" not in summary:
        summary["titles_detected"] = len(titles_out)
    if summary:
        parsed["summary"] = summary
    if titles_out:
        apply_title_scores(parsed, preferences=preferences)
    formatted = format_disc_overview(parsed)
    if formatted:
        parsed["formatted"] = formatted
    return parsed
