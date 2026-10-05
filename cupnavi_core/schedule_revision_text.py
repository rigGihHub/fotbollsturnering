"""Conservative, AI-independent reading of existing match rows in text PDFs."""
from __future__ import annotations

import re
import unicodedata

from .ai_cup_document_import import _extract_pdf_text

TIME = re.compile(r"(?<![\d:])(?:(\d{4}-\d{2}-\d{2})[ T])?([01]?\d|2[0-3])[:.]([0-5]\d)(?!\d)", re.I)


def _norm(value):
    return unicodedata.normalize("NFKC", str(value or "")).casefold().translate(str.maketrans("‐‑‒–—−", "------"))


def _label_pattern(label):
    # Optional whitespace supports PDF line wraps and PremiumBarcelona, without
    # accepting fuzzy spellings or a short name inside another team's name.
    words = _norm(label).split()
    return re.compile(r"(?<!\w)" + r"\s*".join(re.escape(word) for word in words) + r"(?!\w)")


def extract_schedule_revision_text(documents, schedule):
    labels = sorted({str(row[key]) for row in schedule.get("matches", [])
                     for key in ("home_label", "away_label") if row.get(key) and not str(row[key]).startswith(("team:", "group:", "match:"))})
    teams = [(label, _label_pattern(label)) for label in labels]
    venues = [(str(name), _label_pattern(name)) for name in (schedule.get("pitch_names") or {}).values() if name]
    matches, unread, skipped_files = [], [], []
    for raw, filename, mime in documents:
        lower = str(filename).lower()
        if lower.endswith(".pdf") or mime == "application/pdf":
            text = _extract_pdf_text(raw)
        elif lower.endswith(".txt") or str(mime).startswith("text/"):
            text = raw.decode("utf-8", errors="replace")[:80000]
        else:
            text = ""
        if not text:
            skipped_files.append(filename)
            continue
        text = _norm(text)
        times = list(TIME.finditer(text))
        for index, time in enumerate(times):
            end = times[index + 1].start() if index + 1 < len(times) else len(text)
            block = text[time.end():end].strip()
            if len(block) > 600:
                unread.append(f"{time.group(0)}: texten efter tiden kunde inte avgränsas till en säker matchrad.")
                continue  # Never associate a time with a distant roster/other section.
            hits = [(hit.start(), hit.end(), label) for label, pattern in teams for hit in pattern.finditer(block)]
            hits.sort()
            found_venues = [name for name, pattern in venues if pattern.search(block)]
            if len(hits) != 2 or hits[0][2] == hits[1][2] or len(found_venues) != 1:
                if (hits or found_venues) and re.search(r"\s(?:-|mot|vs\.?)\s", block):
                    unread.append(f"{time.group(0)} {block[:180]}: lagpar eller plan kunde inte läsas entydigt ur PDF-texten.")
                continue
            between = block[hits[0][1]:hits[1][0]].strip()
            if not re.fullmatch(r"(?:-|mot|vs\.?)", between):
                continue  # Two names alone can be a roster or commentary.
            group = re.search(r"\b(?:grupp|group)\s*[:.-]?\s*([a-zåäö]|\d+)\b", block)
            clock = f"{int(time.group(2)):02d}:{time.group(3)}"
            matches.append({"home_team": hits[0][2], "away_team": hits[1][2],
                            "time": f"{time.group(1)}T{clock}" if time.group(1) else clock,
                            "venue": found_venues[0], "group_name": group.group(1) if group else None})
    if not matches:
        return None
    warnings = ["Matchraderna lästes från dokumentets text utan AI. Kontrollera förslagen innan du genomför ändringarna. Endast tider och planer för dessa matchrader jämförs."]
    if skipped_files:
        unread.extend(f"{name}: ingen läsbar schematext. Filen kunde inte jämföras utan AI." for name in skipped_files)
    return {"matches": matches, "warnings": warnings, "unread_rows": unread, "extraction_method": "pdf_text"}
