"""Thread-safe public PDF snapshot + rendering for deferred Streamlit downloads."""
from __future__ import annotations

from typing import Any, Callable

from cupnavi_core.pdf_export import build_cup_program_pdf


def _dict_rows(cursor):
    columns = [item[0] for item in (cursor.description or ())]
    rows = cursor.fetchall()
    result = []
    for row in rows:
        if hasattr(row, "keys"):
            result.append(dict(row))
        else:
            result.append(dict(zip(columns, row)))
    return result


def _dict_one(cursor):
    columns = [item[0] for item in (cursor.description or ())]
    row = cursor.fetchone()
    if row is None:
        return None
    if hasattr(row, "keys"):
        return dict(row)
    return dict(zip(columns, row))


def build_public_pdf_download(
    tournament_id: int,
    tournament: Any,
    *,
    open_read_connection: Callable[[], Any],
) -> bytes:
    """Read one independent DB snapshot and return validated PDF bytes.

    The connection factory must not rely on Streamlit session state because
    deferred ``st.download_button`` callables execute in a worker thread.
    """
    tournament_id = int(tournament_id)
    raw = open_read_connection()
    try:
        pdf_matches = _dict_rows(raw.execute(
            """SELECT * FROM matches
               WHERE tournament_id=? AND scheduled_start IS NOT NULL AND schedule_published=1
               ORDER BY scheduled_start,pitch_number,id""",
            (tournament_id,),
        ))
        pdf_teams = _dict_rows(raw.execute("SELECT * FROM teams WHERE tournament_id=? ORDER BY name", (tournament_id,)))
        pdf_groups = _dict_rows(raw.execute("SELECT * FROM groups WHERE tournament_id=? ORDER BY name", (tournament_id,)))
        pdf_refs = _dict_rows(raw.execute("SELECT * FROM referees WHERE tournament_id=? ORDER BY name", (tournament_id,)))
        pdf_rules = _dict_one(raw.execute("SELECT * FROM schedule_rules WHERE tournament_id=?", (tournament_id,))) or {}
        pdf_pitches = _dict_rows(raw.execute("SELECT * FROM pitches WHERE tournament_id=? ORDER BY pitch_number", (tournament_id,)))
    finally:
        try:
            raw.close()
        except Exception:
            pass

    team_names = {int(row["id"]): str(row.get("name") or "Okänt lag") for row in pdf_teams}
    group_names = {int(row["id"]): str(row.get("name") or "Grupp") for row in pdf_groups}
    match_numbers = {int(row["id"]): index for index, row in enumerate(pdf_matches, 1)}

    def source_label(source):
        parts = str(source or "").split(":")
        try:
            if len(parts) >= 2 and parts[0] == "team":
                return team_names.get(int(parts[1]), "Okänt lag")
            if len(parts) >= 3 and parts[0] == "group":
                group_name = group_names.get(int(parts[1]), "Grupp")
                rank = int(parts[2])
                return f"Vinnaren i {group_name}" if rank == 1 else f"{rank}:an i {group_name}"
            if len(parts) >= 2 and parts[0] in {"winner", "loser"}:
                number = match_numbers.get(int(parts[1]))
                prefix = "Vinnare" if parts[0] == "winner" else "Förlorare"
                return f"{prefix} match {number}" if number else f"{prefix} i tidigare match"
        except (TypeError, ValueError):
            pass
        return "Ej klart"

    pdf_sources = {
        source
        for match_row in pdf_matches
        for source in (match_row.get("home_source"), match_row.get("away_source"))
        if source
    }
    source_labels = {source: source_label(source) for source in pdf_sources}
    source_team_ids = {}
    for source in pdf_sources:
        parts = str(source).split(":")
        if len(parts) >= 2 and parts[0] == "team":
            try:
                source_team_ids[source] = int(parts[1])
            except (TypeError, ValueError):
                pass

    tournament_keys = (
        "name", "location", "tournament_date", "start_date", "end_date",
        "table_tiebreak", "playoff_tie_rule", "extra_time_minutes",
        "public_information", "organizer_phone", "instagram_url",
    )
    tournament_payload = {key: tournament[key] for key in tournament_keys if key in tournament.keys()}
    match_keys = (
        "id", "group_id", "stage", "scheduled_start", "pitch_number",
        "home_source", "away_source", "home_score", "away_score",
        "home_penalties", "away_penalties", "referee_id",
    )
    match_payload = [{key: row.get(key) for key in match_keys} for row in pdf_matches]
    team_payload = [{key: row.get(key) for key in ("id", "name", "group_id", "primary_color", "secondary_color")} for row in pdf_teams]
    group_payload = [{key: row.get(key) for key in ("id", "name")} for row in pdf_groups]
    ref_payload = [{key: row.get(key) for key in ("id", "name")} for row in pdf_refs]

    data = build_cup_program_pdf(
        tournament_payload, match_payload, team_payload, group_payload, ref_payload,
        source_labels, source_team_ids, rules=pdf_rules, pitches=pdf_pitches,
    )
    data = bytes(data) if isinstance(data, (bytes, bytearray)) else b""
    if len(data) < 1000 or not data.startswith(b"%PDF") or b"%%EOF" not in data[-64:]:
        raise ValueError("CupNavi kunde inte skapa en komplett giltig PDF.")
    return data
