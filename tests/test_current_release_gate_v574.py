from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT/'app.py').read_text(encoding='utf-8')
KIT = (ROOT/'cupnavi_core'/'ai_kit_suggestion.py').read_text(encoding='utf-8')
VERSION = (ROOT/'cupnavi_core'/'version.py').read_text(encoding='utf-8')


def test_v574_uses_bounded_fallback_search_strategies_for_youth_teams():
    assert '2026.09.09-574-MULTI-STRATEGY-YOUTH-KIT-SEARCH' in VERSION
    assert 'MAX_SEARCH_ATTEMPTS = 3' in KIT
    assert 'Exakt lag + cupkontext' in KIT
    assert 'Klubbnamn utan ungdomssuffix' in KIT
    assert 'Lokala och visuella källor' in KIT
    assert 'if result.get("found")' in KIT


def test_v574_can_strip_common_youth_suffixes_without_claiming_identity():
    assert 'def likely_club_name' in KIT
    assert 'Svart|Blå|Bla|Röd|Rod|Vit|Grön|Gron' in KIT
    assert 'Gissa aldrig klubbidentitet' in KIT


def test_v574_single_team_scan_keeps_tournament_context_and_hint():
    block = APP[APP.index('if admin_page == "Tröj setup"'):APP.index('if admin_page == "Grupper"')]
    assert 'location=_row_value(tournament, "location", "")' in block
    assert 'country_code=_row_value(tournament, "country_code", "")' in block
    assert 'age_class=_row_value(team, "age_class", "")' in block
    assert 'search_hint=_kit_hint' in block


def test_v574_shows_what_was_tried_but_never_auto_approves():
    assert 'Sökvägar provade:' in APP
    assert 'Hittat via:' in APP
    assert 'Godkänn och spara' in APP
    assert 'if result.get("found")' in KIT
    # Search remains suggestion-only; persistence is still tied to explicit approval button.
    kit_block = APP[APP.index('if admin_page == "Tröj setup"'):APP.index('if admin_page == "Grupper"')]
    assert kit_block.index('if approve_col.button("✓ Godkänn och spara"') < kit_block.index('UPDATE teams SET primary_color=')
