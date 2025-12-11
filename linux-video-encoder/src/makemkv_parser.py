import re
from typing import Any, Dict, List, Optional


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
    # Prefer titles >=10 minutes; otherwise show top 3 by duration
    def title_duration(t):
        return t.get("duration_seconds") or 0

    long_titles = [t for t in titles if title_duration(t) >= 600]
    selected = long_titles if long_titles else sorted(titles, key=title_duration, reverse=True)[:3]

    for t in sorted(selected, key=title_duration, reverse=True):
        parts = []
        label = f"Title {t.get('id', '?')}"
        if t.get("playlist"):
            label += f" ({t['playlist']})"
        parts.append(label)
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
        lines.append(" | ".join(parts))
    return "\n".join([ln for ln in lines if ln])


def parse_makemkv_info_output(raw: str) -> Dict[str, Any]:
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
    tinfo_re = re.compile(r'^TINFO:(\d+),(\d+),(\d+),([^,]*),"(.*)"$')
    sinfo_re = re.compile(r'^SINFO:(\d+),(\d+),(\d+),(\d+),"(.*)"$')
    drv_re = re.compile(r'^DRV:\d+,\d+,\d+,\d+,"([^"]*)"(?:,"([^"]*)")?')
    msg_title_re = re.compile(
        r"Title #(?P<playlist>\d+)[^\n]*length (?P<length>[0-9:]+)(?:[^\d]+(?P<chapters>\d+) chapters)?",
        re.IGNORECASE,
    )

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

    for line in raw.splitlines():
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
        tinfo_match = tinfo_re.match(ln)
        if tinfo_match:
            title_id = int(tinfo_match.group(1))
            info_id = int(tinfo_match.group(2))
            value = (tinfo_match.group(5) or "").strip()
            lang = (tinfo_match.group(4) or "").strip()
            entry = ensure_title(title_id)
            entry["tinfo"].append(ln)
            if info_id == 2 and value:
                entry["source"] = value
                pl_match = re.search(r"#(\d+)", value)
                if pl_match:
                    entry["playlist"] = pl_match.group(1).lstrip("0") or pl_match.group(1)
            if info_id == 8:
                # Often chapters or duration depending on drive; prefer numeric chapters first
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
            continue
        sinfo_match = sinfo_re.match(ln)
        if sinfo_match:
            title_id = int(sinfo_match.group(1))
            stream_id = int(sinfo_match.group(2))
            field_id = int(sinfo_match.group(3))
            value = (sinfo_match.group(5) or "").strip()
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
            if lower.startswith("audio:"):
                entry["audio_tracks"].append(value.split(":", 1)[1].strip() or value)
            elif lower.startswith("subtitle"):
                entry["subtitle_tracks"].append(value.split(":", 1)[1].strip() or value)
            elif lower.startswith("video"):
                entry.setdefault("video", value.split(":", 1)[1].strip() or value)

    # Merge inferred data and clean up lists
    titles_out: List[Dict[str, Any]] = []
    for idx in sorted(titles.keys()):
        entry = titles[idx]
        playlist = entry.get("playlist")
        if not playlist and entry.get("source"):
            pl_match = re.search(r"#?0*([0-9]{1,5})", entry["source"])
            if pl_match:
                entry["playlist"] = pl_match.group(1)
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
    if titles_out:
        try:
            main = max(titles_out, key=lambda t: t.get("duration_seconds") or 0)
        except Exception:
            main = None
        if main and main.get("duration_seconds"):
            summary["main_feature"] = {
                "id": main.get("id"),
                "playlist": main.get("playlist"),
                "duration": main.get("duration"),
                "chapters": main.get("chapters"),
            }
        summary["title_count"] = len(titles_out)
    if summary:
        parsed["summary"] = summary
    formatted = format_disc_overview(parsed)
    if formatted:
        parsed["formatted"] = formatted
    return parsed
