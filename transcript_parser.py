"""
transcript_parser.py — Parses .txt, .srt (YouTube), .vtt transcripts.
"""
import re, os
from dataclasses import dataclass
from typing import Optional

@dataclass
class TranscriptDocument:
    filename: str
    format: str
    raw_text: str
    clean_text: str
    segments: list[dict]
    word_count: int = 0
    estimated_duration_min: float = 0.0
    language_hint: str = "unknown"

    def __post_init__(self):
        self.word_count = len(self.clean_text.split())
        self.language_hint = _detect_script(self.clean_text)

def parse(filepath: str) -> TranscriptDocument:
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Transcript file not found: {filepath}")
    with open(filepath, "r", encoding="utf-8") as f:
        raw = f.read()
    ext = os.path.splitext(filepath)[1].lower()
    filename = os.path.basename(filepath)
    if ext == ".srt":
        return _parse_srt(filename, raw)
    elif ext == ".vtt":
        return _parse_vtt(filename, raw)
    else:
        return _parse_txt(filename, raw)

def _parse_txt(filename, raw):
    clean = _normalize_whitespace(raw)
    return TranscriptDocument(filename=filename, format="txt", raw_text=raw,
                               clean_text=clean, segments=[{"text": clean}])

def _parse_srt(filename, raw):
    raw = raw.lstrip("\ufeff")
    blocks = re.split(r"\n{2,}", raw.strip())
    segments, text_lines = [], []
    for block in blocks:
        lines = block.strip().splitlines()
        if not lines:
            continue
        body = lines[1:] if re.match(r"^\d+$", lines[0].strip()) else lines
        if not body:
            continue
        start_ts = end_ts = None
        content_start = 0
        ts_match = re.match(
            r"(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s+-->\s+(\d{2}:\d{2}:\d{2}[,\.]\d{3})", body[0])
        if ts_match:
            start_ts, end_ts, content_start = ts_match.group(1), ts_match.group(2), 1
        text = re.sub(r"<[^>]+>", "", " ".join(body[content_start:]).strip()).strip()
        if not text:
            continue
        seg = {"text": text}
        if start_ts:
            seg["start"], seg["end"] = start_ts, end_ts
        segments.append(seg)
        text_lines.append(text)
    clean = _normalize_whitespace(" ".join(text_lines))
    return TranscriptDocument(filename=filename, format="srt", raw_text=raw,
                               clean_text=clean, segments=segments,
                               estimated_duration_min=_estimate_duration_from_srt(segments))

def _parse_vtt(filename, raw):
    raw = raw.lstrip("\ufeff")
    raw = re.sub(r"^WEBVTT.*?\n", "", raw, flags=re.MULTILINE)
    raw = re.sub(r"NOTE[^\n]*\n.*?\n\n", "", raw, flags=re.DOTALL)
    raw = re.sub(r"STYLE[^\n]*\n.*?\n\n", "", raw, flags=re.DOTALL)
    doc = _parse_srt(filename, raw)
    doc.format = "vtt"
    return doc

def _normalize_whitespace(text):
    return re.sub(r"\n{3,}", "\n\n", re.sub(r"[ \t]+", " ", text)).strip()

def _estimate_duration_from_srt(segments):
    last = next((s for s in reversed(segments) if "end" in s), None)
    return _ts_to_seconds(last["end"]) / 60.0 if last else 0.0

def _ts_to_seconds(ts):
    ts = ts.replace(",", ".")
    try:
        h, m, s = (float(x) for x in ts.split(":"))
        return h * 3600 + m * 60 + s
    except (ValueError, AttributeError):
        return 0.0

def _detect_script(text):
    arabic = sum(1 for c in text if "\u0600" <= c <= "\u06ff")
    latin = sum(1 for c in text if c.isalpha() and c.isascii())
    total = arabic + latin
    if total == 0:
        return "unknown"
    r = arabic / total
    return "arabic" if r > 0.7 else "latin" if r < 0.3 else "mixed"
