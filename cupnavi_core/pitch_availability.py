"""Multiple availability intervals with a backwards-compatible first interval.

The original day row is retained. Extra intervals never turn the closed gap
into availability; all scheduling readers must expand them before use.
"""
import json
from datetime import datetime


def ensure_pitch_intervals_schema(con):
    columns = {row[1] for row in con.execute("PRAGMA table_info(pitch_day_windows)").fetchall()}
    if columns and "additional_windows_json" not in columns:
        try:
            con.execute("ALTER TABLE pitch_day_windows ADD COLUMN additional_windows_json TEXT NOT NULL DEFAULT '[]'")
        except Exception as exc:
            if "duplicate column" not in str(exc).lower():
                raise


def validate_intervals(intervals):
    if not intervals or len(intervals) > 50:
        raise ValueError("Ange mellan 1 och 50 tidsfönster per plan och dag")
    clean = []
    for row in intervals:
        try:
            start = datetime.strptime(str(row["start_time"]), "%H:%M").strftime("%H:%M")
            end = datetime.strptime(str(row["end_time"]), "%H:%M").strftime("%H:%M")
        except (ValueError, KeyError, TypeError) as exc:
            raise ValueError("Plantider måste anges som HH:MM") from exc
        if start >= end:
            raise ValueError("Sluttiden måste vara senare än starttiden")
        clean.append({"start_time": start, "end_time": end})
    clean.sort(key=lambda row: row["start_time"])
    for previous, current in zip(clean, clean[1:]):
        if current["start_time"] < previous["end_time"]:
            raise ValueError(f"Tidsfönstren {previous['start_time']}–{previous['end_time']} och {current['start_time']}–{current['end_time']} överlappar på samma plan och dag")
    return clean


def expand_pitch_windows(rows):
    result = []
    for raw in rows:
        row = dict(raw)
        extra = json.loads(row.pop("additional_windows_json", None) or "[]")
        intervals = validate_intervals([row, *extra])
        for interval in intervals:
            result.append({**row, **interval})
    return result


def write_pitch_intervals(con, tournament_id, pitch_number, play_date, intervals, confirmed=True):
    clean = validate_intervals(intervals)
    ensure_pitch_intervals_schema(con)
    values = (clean[0]["start_time"], clean[0]["end_time"], int(bool(confirmed)), json.dumps(clean[1:], separators=(",", ":")))
    key = (int(tournament_id), int(pitch_number), str(play_date))
    current = con.execute("SELECT start_time,end_time,confirmed,additional_windows_json FROM pitch_day_windows WHERE tournament_id=? AND pitch_number=? AND play_date=?", key).fetchone()
    if current and tuple(current) == values:
        return False
    con.execute("""INSERT INTO pitch_day_windows(tournament_id,pitch_number,play_date,start_time,end_time,confirmed,additional_windows_json)
        VALUES(?,?,?,?,?,?,?) ON CONFLICT(tournament_id,pitch_number,play_date) DO UPDATE SET
        start_time=excluded.start_time,end_time=excluded.end_time,confirmed=excluded.confirmed,additional_windows_json=excluded.additional_windows_json""", (*key, *values))
    return True
