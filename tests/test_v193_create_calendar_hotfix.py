from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")


def test_new_tournament_uses_schema_compatible_insert():
    assert "def insert_tournament_compat(payload):" in APP
    assert "available = _connection_columns(con, \"tournaments\")" in APP
    assert "new_tournament_id = insert_tournament_compat({" in APP


def test_calendar_weekday_headers_have_explicit_contrast():
    assert '[role="columnheader"]' in APP
    assert "font-weight:700 !important" in APP
    assert "color:#0f172a !important" in APP


def test_visible_version_remains_192_hotfix():
    assert "Version v.1.249" in APP
