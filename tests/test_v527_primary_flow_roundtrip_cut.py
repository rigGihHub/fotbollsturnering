from pathlib import Path

APP = Path("app.py").read_text(encoding="utf-8")

def test_primary_setup_pages_skip_full_sidebar_rules_roundtrip():
    assert '_need_full_sidebar_rules = admin_page in {"Skapa och publicera schema", "Kontroller"} or _flow_index is None' in APP
    assert 'elif _flow_counts is not None:\n    sidebar_rules = _flow_counts' in APP

def test_overview_reuses_existing_aggregate_for_referee_mode():
    assert '(SELECT referee_mode FROM schedule_rules WHERE tournament_id=? LIMIT 1) AS referee_mode' in APP

def test_version():
    assert '2026.09.07-527-PRIMARY-FLOW-ROUNDTRIP-CUT' in Path("VERSION.txt").read_text()
