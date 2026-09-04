from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()
TEAM = (ROOT / "cupnavi_core/public_team_follow_view.py").read_text(encoding="utf-8")
LOGIC = (ROOT / "cupnavi_core/public_team_follow.py").read_text(encoding="utf-8")


def test_v446_contract_survives_current_release():
    assert VERSION == "2026.09.04-449-MOBILE-PLAYOFF-ACTION"


def test_next_match_has_direct_single_rerun_action():
    assert 'return "⚽ Öppna nästa match"' in LOGIC
    assert "def _open_public_next_match()" in TEAM
    assert "on_click=_open_public_next_match" in TEAM
    assert 'st.query_params["match"] = str(_favorite_next_id)' in TEAM


def test_next_match_action_reuses_snapshot_without_db_read():
    block = TEAM[
        TEAM.index("# v446: the hero already contains the next-match facts"):
        TEAM.index("# v447: put navigation to the next pitch")
    ]
    assert 'row_value(favorite_next, "id", 0)' in block
    assert "one_row(" not in block
    assert "all_rows(" not in block
    assert "st.rerun(" not in block
