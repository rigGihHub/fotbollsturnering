from pathlib import Path

from cupnavi_core.public_search import build_public_search_results

ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()
WORKSPACE = (ROOT / "cupnavi_core" / "public_workspace_view.py").read_text(encoding="utf-8")
MATCHES_VIEW = (ROOT / "cupnavi_core" / "public_matches_view.py").read_text(encoding="utf-8")


def _row_value(row, key, default=None):
    return row.get(key, default)


def _source_team_id(source):
    parts = str(source or "").split(":")
    return int(parts[1]) if len(parts) == 2 and parts[0] == "team" else None


def _source_label(source):
    team_id = _source_team_id(source)
    return {1: "Örebro SK", 2: "AIK"}.get(team_id, str(source))


def test_public_search_finds_team_pitch_and_match_without_database_logic():
    teams = [
        {"id": 1, "name": "Örebro SK", "age_class": "P2014"},
        {"id": 2, "name": "AIK", "age_class": "P2014"},
    ]
    matches = [{
        "id": 17,
        "home_source": "team:1",
        "away_source": "team:2",
        "scheduled_start": "2026-09-05T10:00:00",
        "pitch_number": 2,
        "pitch_name": "Sörbyvallen 2",
        "stage": "Grupp A",
    }]
    pitches = [{"pitch_number": 2, "name": "Sörbyvallen 2", "address": "Sörbyängsvägen"}]

    kwargs = dict(
        teams=teams,
        matches=matches,
        pitches=pitches,
        team_names={1: "Örebro SK", 2: "AIK"},
        source_team_id=_source_team_id,
        source_label=_source_label,
        pitch_label=lambda row: row.get("pitch_name") or f"Plan {row.get('pitch_number')}",
        datetime_label=lambda value: str(value),
        row_value=_row_value,
    )
    assert build_public_search_results("Örebro", **kwargs)[0].kind == "team"
    assert any(r.kind == "pitch" for r in build_public_search_results("Sörby", **kwargs))
    assert any(r.kind == "match" and r.identity == 17 for r in build_public_search_results("AIK", **kwargs))
    assert any(r.kind == "match" and r.identity == 17 for r in build_public_search_results("match 17", **kwargs))


def test_public_search_is_submit_driven_and_preserves_info_fast_path():
    assert VERSION == "2026.09.04-449-MOBILE-PLAYOFF-ACTION"
    assert 'with st.form(key=f"public_global_search_form_{tournament_id}"' in WORKSPACE
    assert 'form_submit_button("Sök"' in WORKSPACE
    assert 'or bool(_active_public_search)' in WORKSPACE
    assert 'public_page != "Info" or bool(_active_public_search)' in WORKSPACE
    assert 'SELECT pitch_number,name,address FROM pitches' in WORKSPACE


def test_search_result_can_open_exact_published_match():
    assert 'match_query = st.query_params.get("match")' in WORKSPACE
    assert 'requested_match_id=requested_match_id' in WORKSPACE
    assert 'if requested_match_id:' in MATCHES_VIEW
    assert 'Du visar match {requested_match_id}' in MATCHES_VIEW
