from pathlib import Path

VERSION = "2026.09.07-507-REVIEWED-DOCUMENT-SCHEDULE-IMPORT"
APP = Path("app.py").read_text(encoding="utf-8")
CARDS = Path("cupnavi_core/public_match_cards.py").read_text(encoding="utf-8")


def test_version_is_v463():
    assert VERSION in APP
    assert Path("VERSION.txt").read_text().strip() == VERSION


def test_mobile_cards_are_tighter():
    assert ".public-match-card{padding:10px!important;margin:7px 0!important" in CARDS
    assert ".cn-match-teams{gap:6px;margin-top:7px}" in CARDS


def test_mobile_hides_redundant_labels_and_match_number():
    assert ".public-match-card .kit-label{display:none!important}" in CARDS
    assert ".cn-match-context .match-number{display:none!important}" in CARDS


def test_referee_is_only_rendered_when_assigned():
    assert "referee_label = public_referee_label(match_row)" in CARDS
    assert 'if referee_label else ""' in CARDS
    assert '"Ej tillsatt"' not in CARDS


def test_role_labels_are_removed_from_normal_card():
    assert '<small class="kit-label">Hemmalag</small>' not in CARDS
    assert 'if away_kit_used else \'\'' in CARDS


def test_core_scan_information_remains():
    for marker in (
        "cn-match-time",
        "cn-match-place",
        "public-team-name",
        "match-score",
        "status-pill",
    ):
        assert marker in CARDS
