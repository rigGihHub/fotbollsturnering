"""Preview and explicitly apply a new rank-based round-robin playoff."""
import json
from itertools import combinations

from cupnavi_core.placement_playoffs import DRAW_RULE, GROUP_PLAYOFF_FORMAT, all_placement_blocks
from cupnavi_core.bracket_validation import validate_bracket_sources
from .admin_repository import _has_tournament_access
from .repository import connect
from .playoff_import_repository import _resolve_source, _parse_start, _group_key, commit_playoff_import
from .playoff_plan_state import capture_plan_state, plan_hash, assert_replaceable, assert_no_match_events, latest_backup, rows


def preview_group_playoffs(account_id, cup_id, source_rows=None, source_name=None):
    if not _has_tournament_access(account_id, cup_id):
        return None
    with connect() as con:
        state = capture_plan_state(con, cup_id)
        assert_replaceable(state)
        assert_no_match_events(con, state)
        if source_rows is None:
            groups_by_id = {g["id"]: g["name"] for g in state["groups"]}
            pitch_names = {p["pitch_number"]: p["name"] for p in state["pitches"]}
            blocks = all_placement_blocks(state["matches"])
            if blocks:
                source_rows = []
                for block in blocks:
                    for match in block["matches"]:
                        def label(source):
                            kind, group_id, rank = source.split(":")
                            if kind != "group":
                                raise ValueError("Det befintliga gruppspelet har direkta lagnamn. Välj ett nytt underlag eller skapa från grundgrupperna.")
                            return f"{rank}:a grupp {groups_by_id[int(group_id)]}"
                        source_rows.append({"label": block["name"], "home_source": label(match["home_source"]), "away_source": label(match["away_source"]), "time": match.get("scheduled_start"), "venue": pitch_names.get(match.get("pitch_number"))})
                source_name = "Befintligt placeringsgruppspel"
            elif con.execute("PRAGMA table_info(tournament_setup_imports)").fetchall():
                found = rows(con.execute("SELECT payload_json,source_name FROM tournament_setup_imports WHERE tournament_id=? AND import_kind='initial_setup' ORDER BY id DESC LIMIT 1", (cup_id,)))
                if found:
                    payload = json.loads(found[0]["payload_json"])
                    source_rows = payload.get("playoff_matches") or []
                    source_name = source_name or found[0]["source_name"]
    assert_replaceable(state)
    groups = state["groups"]
    group_map = {g["name"].casefold(): g["id"] for g in groups}
    imported = list(source_rows or [])
    imported_map = {}
    from datetime import date
    cup = state["cup"]
    fallback = date.fromisoformat(str(cup["start_date"])) if cup.get("start_date") and (not cup.get("end_date") or cup["end_date"] == cup["start_date"]) else None
    pitches = {str(p["name"]).casefold(): p for p in state["pitches"]}
    for row in imported:
        h, error = _resolve_source(row.get("home_source"), {}, group_map, {})
        a, other = _resolve_source(row.get("away_source"), {}, group_map, {})
        if error or other:
            raise ValueError(f"Underlaget passar inte {cup.get('name') or 'aktiv cup'}: {error or other}. Kontrollera att rätt cup är vald och att PDF:ens grupper finns i cupen.")
        parts = [source.split(":") for source in (h, a)]
        if any(p[0] != "group" for p in parts) or parts[0][2] != parts[1][2] or h == a:
            raise ValueError("Nytt gruppspel kräver ettor mot ettor, tvåor mot tvåor osv., utan vinnar-/förlorarkopplingar.")
        key = tuple(sorted((h, a)))
        if key in imported_map:
            raise ValueError("Underlaget innehåller samma placeringsmatch flera gånger.")
        start = _parse_start(row.get("time"), fallback)
        if start and (cup.get("start_date") and start[:10] < cup["start_date"] or cup.get("end_date") and start[:10] > cup["end_date"]):
            raise ValueError("En slutspelstid i PDF:en ligger utanför cupens datum. Kontrollera Cupinfo.")
        venue = str(row.get("venue") or "").strip()
        if venue and sum(str(p["name"]).casefold() == venue.casefold() for p in state["pitches"]) > 1:
            raise ValueError(f"Flera planer heter {venue}. Ge planerna unika namn innan formatbytet.")
        if venue and venue.casefold() not in pitches:
            raise ValueError(f"Planen '{venue}' från underlaget saknas i cupen. Lägg till eller rätta planen under Planer & tider först.")
        if bool(start) != bool(venue):
            raise ValueError("Varje PDF-match behöver både tid och plan, eller inget av dem.")
        imported_map[key] = {**row, "time": start, "venue": venue or None}
    if len(groups) < 3:
        raise ValueError("Detta placeringsgruppspel kräver minst tre grundgrupper. Aktiv cup har " + str(len(groups)) + ". PDF:ens grupper måste först finnas i rätt cup.")
    sizes = [sum(t.get("group_id") == g["id"] for t in state["teams"]) for g in groups]
    if not sizes or min(sizes) < 1 or len(set(sizes)) != 1:
        raise ValueError("Grundgrupperna behöver ha samma antal lag innan ettor, tvåor och treor kan delas upp i nya grupper.")
    proposal, levels = [], []
    expected = set()
    for rank in range(1, sizes[0] + 1):
        label = {1: "GULDGRUPPEN", 2: "SILVERGRUPPEN", 3: "BRONSGRUPPEN"}.get(rank, f"PLACERINGSGRUPP {rank}")
        level_rows = []
        for h, a in combinations(groups, 2):
            key = tuple(sorted((f"group:{h['id']}:{rank}", f"group:{a['id']}:{rank}")))
            expected.add(key)
            original = imported_map.get(key)
            item = {"label": label, "home_source": f"{rank}:a grupp {h['name']}", "away_source": f"{rank}:a grupp {a['name']}", "time": None, "venue": None}
            if original:
                item.update({k: original.get(k) for k in ("home_source", "away_source", "time", "venue", "duration")})
            proposal.append(item); level_rows.append(item)
        levels.append({"name": label, "placement": rank, "participant_count": len(groups), "matches": level_rows})
    if imported and set(imported_map) != expected:
        raise ValueError("PDF:ens matcher täcker inte exakt de nya placeringsgrupperna. Alla lag i varje nivå måste möta varandra en gång.")
    if len(proposal) > 128:
        raise ValueError("Upplägget blir större än 128 slutspelsmatcher. Välj ett mindre upplägg.")
    return {"cup_name": cup.get("name"), "format": GROUP_PLAYOFF_FORMAT, "revision": plan_hash(state), "source_name": source_name,
            "replaced_count": sum(m.get("bracket_id") is not None for m in state["matches"]),
            "locked_time_count": sum(m.get("bracket_id") is not None and bool(m.get("schedule_locked")) for m in state["matches"]),
            "match_count": len(proposal), "scheduled_count": sum(bool(m["time"]) for m in proposal), "levels": levels, "matches": proposal}


def apply_group_playoffs(account_id, cup_id, revision, source_rows=None, source_name=None):
    proposal = preview_group_playoffs(account_id, cup_id, source_rows, source_name)
    if proposal is None:
        return None
    if revision != proposal["revision"]:
        raise ValueError("Cupen har ändrats sedan förhandsgranskningen. Förhandsgranska igen.")
    result = commit_playoff_import(account_id, cup_id, proposal["matches"], {"tie_rule": DRAW_RULE}, replace_revision=revision, format_override=GROUP_PLAYOFF_FORMAT)
    return result


def restore_previous_playoffs(account_id, cup_id):
    if not _has_tournament_access(account_id, cup_id):
        return None
    with connect() as con:
        try:
            con.execute("BEGIN")
            backup = latest_backup(con, cup_id)
            if not backup:
                raise ValueError("Det finns inget tidigare slutspelsupplägg att återställa.")
            saved = json.loads(backup["payload_json"])
            current = capture_plan_state(con, cup_id)
            assert_replaceable(current)
            assert_no_match_events(con, current)
            if plan_hash(capture_plan_state(con, cup_id, playoffs_only=True)) != saved["after_hash"]:
                raise ValueError("Det nya slutspelet har ändrats. Det tidigare upplägget kan inte återställas automatiskt.")
            for table in ("matches", "brackets"):
                for row in saved["before"][table]:
                    occupied = con.execute(f"SELECT tournament_id FROM {table} WHERE id=?", (row["id"],)).fetchone()
                    if occupied and occupied[0] != cup_id:
                        raise ValueError("Det tidigare uppläggets id används av en annan cup och kan inte återställas.")
            con.execute("DELETE FROM matches WHERE tournament_id=? AND bracket_id IS NOT NULL", (cup_id,))
            con.execute("DELETE FROM brackets WHERE tournament_id=?", (cup_id,))
            before = saved["before"]
            for table in ("brackets", "matches"):
                for row in before[table]:
                    keys = list(row)
                    con.execute(f"INSERT INTO {table}({','.join(keys)}) VALUES({','.join('?' for _ in keys)})", list(row.values()))
            keys = list(before["settings"])
            con.execute(f"UPDATE tournaments SET {','.join(key+'=?' for key in keys)},schedule_dirty=1,is_published=0,admin_revision=COALESCE(admin_revision,0)+1 WHERE id=?", (*before["settings"].values(), cup_id))
            matches = rows(con.execute("SELECT * FROM matches WHERE tournament_id=?", (cup_id,)))
            teams = rows(con.execute("SELECT id FROM teams WHERE tournament_id=?", (cup_id,)))
            groups = rows(con.execute("SELECT id FROM groups WHERE tournament_id=?", (cup_id,)))
            if not validate_bracket_sources(matches, teams, groups).get("ready"):
                raise ValueError("Det tidigare slutspelets deltagarkällor är inte längre giltiga.")
            con.execute("UPDATE tournament_setup_imports SET import_kind='playoff_format_restored' WHERE id=? AND tournament_id=?", (backup["id"], cup_id))
            con.commit()
        except Exception:
            con.rollback(); raise
    return {"restored": True}
