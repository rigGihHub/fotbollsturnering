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
    matches, playoff_matches, unread, skipped_files = [], [], [], []
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
        table_columns = bool(re.search(r"tid\s+plan\s+grp\s+hemma\s+borta", text))
        times = list(TIME.finditer(text))
        for index, time in enumerate(times):
            line_prefix = text[:time.start()].rsplit("\n", 1)[-1]
            if not re.fullmatch(r"\s*(?:\d+[.)]?\s+)?", line_prefix):
                continue  # A time in commentary is not a schedule row.
            end = times[index + 1].start() if index + 1 < len(times) else len(text)
            block = text[time.end():end].strip()
            if table_columns or re.search(r"tid\s+plan\s+serie\s+match", text):
                block = re.split(r"(?<=-)\s*\n", block, maxsplit=1)[0].strip()
            if len(block) > 600:
                unread.append(f"{time.group(0)}: texten efter tiden kunde inte avgränsas till en säker matchrad.")
                continue  # Never associate a time with a distant roster/other section.
            placement = re.fullmatch(r"\s*(.+?)\s+(guldgruppen|silvergruppen|bronsgruppen)\s+(\d+):[ae]\s+(?:i\s+)?grupp\s+([a-zåäö0-9]+)\s*-\s*(\d+):[ae]\s+(?:i\s+)?grupp\s+([a-zåäö0-9]+)\s+(\d+)\s*[×x]\s*(\d+)\s*-?\s*", block)
            if placement:
                venue, label, h_rank, h_group, a_rank, a_group, halves, minutes = placement.groups()
                clock = f"{int(time.group(2)):02d}:{time.group(3)}"
                playoff_matches.append({"label": label.upper(), "home_source": f"{h_rank}:a grupp {h_group.upper()}", "away_source": f"{a_rank}:a grupp {a_group.upper()}", "time": f"{time.group(1)}T{clock}" if time.group(1) else clock, "venue": venue.title(), "duration": f"{halves}×{minutes}"})
                continue
            hits = [(hit.start(), hit.end(), label) for label, pattern in teams for hit in pattern.finditer(block)]
            hits.sort()
            found_venues = [name for name, pattern in venues if pattern.search(block)]
            if len(hits) != 2 or hits[0][2] == hits[1][2] or len(found_venues) != 1:
                if (hits or found_venues) and re.search(r"\s(?:-|mot|vs\.?)\s", block):
                    unread.append(f"{time.group(0)} {block[:180]}: lagpar eller plan kunde inte läsas entydigt ur PDF-texten.")
                continue
            between = block[hits[0][1]:hits[1][0]].strip()
            table_row = table_columns and not between and re.fullmatch(r"\s*" + _label_pattern(found_venues[0]).pattern + r"\s+([a-zåäö]|\d+)\s*", block[:hits[0][0]]) and re.fullmatch(r"\s*-?\s*", block[hits[1][1]:])
            if not table_row and not re.fullmatch(r"(?:-|mot|vs\.?)", between):
                continue  # Two names alone can be a roster or commentary.
            group = re.search(r"\b(?:grupp|group)\s*[:.-]?\s*([a-zåäö]|\d+)\b", block)
            table_group = re.fullmatch(r"\s*" + _label_pattern(found_venues[0]).pattern + r"\s+([a-zåäö]|\d+)\s*", block[:hits[0][0]]) if table_row else None
            clock = f"{int(time.group(2)):02d}:{time.group(3)}"
            matches.append({"home_team": hits[0][2], "away_team": hits[1][2],
                            "time": f"{time.group(1)}T{clock}" if time.group(1) else clock,
                            "venue": found_venues[0], "group_name": group.group(1) if group else table_group.group(1).upper() if table_group else None})
    if not matches and not playoff_matches:
        return None
    warnings = ["Matchraderna lästes från dokumentets text utan AI. Kontrollera förslagen innan du genomför ändringarna. Endast tider och planer för dessa matchrader jämförs."]
    if skipped_files:
        unread.extend(f"{name}: ingen läsbar schematext. Filen kunde inte jämföras utan AI." for name in skipped_files)
    return {"matches": matches, "playoff_matches": playoff_matches, "warnings": warnings, "unread_rows": unread, "extraction_method": "pdf_text"}
