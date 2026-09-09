from pathlib import Path

VERSION = "2026.09.07-525-OPTIONAL-REFEREE-SETUP"
APP = Path("app.py").read_text(encoding="utf-8")
THEME = Path("cupnavi_core/texttv330_theme.py").read_text(encoding="utf-8")


def test_version_is_v489():
    assert Path("VERSION.txt").read_text().strip() == VERSION
    assert VERSION in APP


def test_match_result_system_present():
    assert "V489 · MATCH & RESULT SYSTEM" in THEME
    assert ".public-match-card.is-live" in THEME
    assert ".public-match-card .match-score" in THEME
    assert "font-variant-numeric:tabular-nums" in THEME


def test_live_strip_styled():
    assert ".cn-live-strip" in THEME
    assert ".cn-live-card.is-live" in THEME
    assert ".cn-live-time" in THEME


def test_my_team_styled():
    for selector in [".cn-follow-shell", ".cn-next-card", ".cn-follow-mini", ".cn-follow-latest-result"]:
        assert selector in THEME


def test_public_table_styled():
    assert ".texttv-table" in THEME
    assert ".texttv-table td:nth-child(10)" in THEME
    assert "var(--cn-tt-yellow)" in THEME


def test_theme_is_asset_free():
    block = THEME[THEME.index("V489 · MATCH & RESULT SYSTEM"):]
    assert "@import" not in block
    assert "url(" not in block
    assert "<script" not in block.lower()


def test_mobile_touch_contract_still_present_in_app():
    assert "min-height:44px" in APP
