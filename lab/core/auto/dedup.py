"""Provenance-aware de-duplication. Nothing is corrected; every removed span is recorded.

Rule 1 - margin text in a crop's OCR (the proven 60 px margin can catch neighbouring text):
  a line of the crop's OCR is removed ONLY if it matches (normalized, Arabic-aware) a caption or text
  block that lies OUTSIDE the visual's detected box (the box before the margin was added) and whose
  text is known. Match = the whole normalized line equals a normalized line of that block or the whole
  block, or (lines of >= MIN_SPAN_TOKENS tokens) is a contiguous token run inside the block.
  On digital/mixed pages the block text is the native text layer (native text is preferred, so the
  OCR copy is the one removed). On scanned pages the text of individual blocks is not known (only the
  full page is transcribed), so no line is removed and that is recorded.
Rule 2 - figure text in full-page OCR:
  a span is removed from the full-page OCR only if it is >= MIN_SPAN_TOKENS consecutive tokens that
  match a crop transcription of the SAME page. Each crop token can account for one page occurrence
  only (repeated rows and distinct numbers are kept). A span inside a line whose remaining part has
  >= MIN_SPAN_TOKENS other tokens is ambiguous (body and figure text mixed): it is kept and recorded.
"""

from __future__ import annotations

import re
import unicodedata

MIN_SPAN_TOKENS = 3
_TASHKEEL = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭ]")
_PUNCT = re.compile(r"[^\w%‰٪$€£¥﷼.\-]", re.UNICODE)
_TRANSLATE = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ى": "ي", "ة": "ه", "ـ": "",
                            "٠": "0", "١": "1", "٢": "2", "٣": "3", "٤": "4", "٥": "5", "٦": "6", "٧": "7",
                            "٨": "8", "٩": "9", "۰": "0", "۱": "1", "۲": "2", "۳": "3", "۴": "4", "۵": "5",
                            "۶": "6", "۷": "7", "۸": "8", "۹": "9", "٫": ".", "٬": ",", "−": "-"})


def normalize_token(token: str) -> str:
    """Comparison form only (never written to the document)."""
    text = unicodedata.normalize("NFKC", token).translate(_TRANSLATE)
    text = _TASHKEEL.sub("", text).lower()
    text = _PUNCT.sub("", text).strip(".-")
    return text


def tokens(text: str) -> list[tuple[int, int, str]]:
    """(start, end, normalized) of every token with a non-empty comparison form."""
    out = []
    for match in re.finditer(r"\S+", text or ""):
        norm = normalize_token(match.group())
        if norm:
            out.append((match.start(), match.end(), norm))
    return out


def normalize(text: str) -> str:
    return " ".join(token for _s, _e, token in tokens(text))


def _contains_run(haystack: list[str], needle: list[str]) -> bool:
    n = len(needle)
    return any(haystack[i:i + n] == needle for i in range(len(haystack) - n + 1))


def remove_margin_lines(crop_text: str, outside_blocks: list[dict], *, min_tokens: int = MIN_SPAN_TOKENS,
                        reason: str = "margin text matching a block outside the visual's detected box") -> dict:
    """Rule 1. `outside_blocks`: [{"id", "text", "bbox_pt", "source"}] with KNOWN text."""
    prepared = []
    for block in outside_blocks:
        text = block.get("text") or ""
        if not text.strip():
            continue
        prepared.append((block, normalize(text).split(), {normalize(line) for line in text.splitlines() if normalize(line)}))
    kept_lines, removed = [], []
    for number, line in enumerate((crop_text or "").splitlines()):
        norm = normalize(line).split()
        match = None
        if norm and prepared:
            joined = " ".join(norm)
            for block, block_tokens, block_lines in prepared:
                if joined in block_lines or norm == block_tokens:
                    match = (block, "whole line")
                    break
                if len(norm) >= min_tokens and _contains_run(block_tokens, norm):
                    match = (block, f"contiguous run of {len(norm)} tokens")
                    break
        if match is None:
            kept_lines.append(line)
            continue
        block, how = match
        removed.append({"rule": "margin_line", "line_number": number + 1, "text": line, "reason": reason,
                        "match": how, "matched_block": block.get("id"), "matched_block_source": block.get("source"),
                        "matched_block_bbox_pt": block.get("bbox_pt")})
    return {"text": "\n".join(kept_lines), "removed": removed,
            "checked_blocks": [b.get("id") for b, _t, _l in prepared]}


def remove_figure_spans(page_text: str, crops: dict[str, str], *, min_tokens: int = MIN_SPAN_TOKENS) -> dict:
    """Rule 2. `crops`: {region_id: transcription} of the same page."""
    page = tokens(page_text)
    norms = [t[2] for t in page]
    crop_tokens = {rid: [t[2] for t in tokens(text)] for rid, text in crops.items() if (text or "").strip()}
    index: dict[tuple, list[tuple[str, int]]] = {}
    for rid, seq in crop_tokens.items():
        for i in range(len(seq) - min_tokens + 1):
            index.setdefault(tuple(seq[i:i + min_tokens]), []).append((rid, i))
    used: dict[str, set[int]] = {rid: set() for rid in crop_tokens}
    spans = []
    i = 0
    while i <= len(norms) - min_tokens:
        best = None
        for rid, start in index.get(tuple(norms[i:i + min_tokens]), []):
            if any(p in used[rid] for p in range(start, start + min_tokens)):
                continue
            seq, length = crop_tokens[rid], min_tokens
            while (i + length < len(norms) and start + length < len(seq) and norms[i + length] == seq[start + length]
                   and start + length not in used[rid]):
                length += 1
            if best is None or length > best[2]:
                best = (rid, start, length)
        if best is None:
            i += 1
            continue
        rid, start, length = best
        used[rid].update(range(start, start + length))
        spans.append({"page_tokens": (i, i + length), "region_id": rid, "crop_tokens": (start, start + length)})
        i += length
    # Ambiguity check per line: other tokens on the same line(s) besides the span
    line_of = [page_text.count("\n", 0, t[0]) for t in page]
    removed, ambiguous, cuts = [], [], []
    for span in spans:
        a, b = span["page_tokens"]
        lines = set(line_of[a:b])
        others = sum(1 for k, line in enumerate(line_of) if line in lines and not a <= k < b)
        start_char, end_char = page[a][0], page[b - 1][1]
        record = {"rule": "figure_span", "text": page_text[start_char:end_char], "tokens": b - a,
                  "matched_region": span["region_id"], "char_range": [start_char, end_char]}
        if others >= min_tokens:
            ambiguous.append(record | {"kept": True, "reason": f"line also has {others} other token(s): body and "
                                                                "figure text mixed, kept (ambiguous)"})
            continue
        removed.append(record | {"reason": f"{b - a} consecutive tokens match the transcription of "
                                           f"{span['region_id']} on the same page"})
        cuts.append((start_char, end_char))
    # Rebuild line by line: a line touched by a removal is dropped when nothing comparable remains on it
    # (only whitespace or punctuation such as table pipes); untouched lines, incl. blank ones, stay as they are.
    lines, offset = [], 0
    for line in page_text.split("\n"):
        start, end = offset, offset + len(line)
        offset = end + 1
        touched = [(max(a, start), min(b, end)) for a, b in cuts if a < end and b > start]
        if not touched:
            lines.append(line)
            continue
        kept, last = [], start
        for a, b in sorted(touched):
            kept.append(page_text[last:a])
            last = b
        kept.append(page_text[last:end])
        remainder = "".join(kept)
        if tokens(remainder):
            lines.append(remainder.rstrip())
    text = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
    return {"text": text, "removed": removed, "ambiguous_kept": ambiguous}


def outside_blocks_for(region: dict, blocks: list[dict]) -> list[dict]:
    """Known-text blocks lying outside the region's detected box (before margin) but inside its crop.
    `blocks`: [{"id", "text", "bbox_pt", "source"}]; region: box_pt_before_margin + crop_bbox_pt."""
    inner = region["box_pt_before_margin"]
    crop = region.get("crop_bbox_pt") or inner
    chosen = []
    for block in blocks:
        box = block["bbox_pt"]
        inter_crop = _intersection(box, crop)
        if inter_crop <= 0:
            continue
        inside_detected = _intersection(box, inner) / max(_area(box), 1e-6)
        if inside_detected < 0.5:  # the block lies (mostly) outside the detected visual
            chosen.append(block)
    return chosen


def _area(box) -> float:
    return max(0.0, box[2] - box[0]) * max(0.0, box[3] - box[1])


def _intersection(a, b) -> float:
    return _area([max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])])
