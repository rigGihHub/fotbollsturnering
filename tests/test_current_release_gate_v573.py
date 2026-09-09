from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT/'app.py').read_text(encoding='utf-8')
KIT = (ROOT/'cupnavi_core'/'ai_kit_suggestion.py').read_text(encoding='utf-8')
GUIDE = (ROOT/'cupnavi_core'/'kit_clash_guidance.py').read_text(encoding='utf-8')
WORK = (ROOT/'cupnavi_core'/'schedule_workspace_view.py').read_text(encoding='utf-8')
VERSION = (ROOT/'cupnavi_core'/'version.py').read_text(encoding='utf-8')

def test_v573_release_and_youth_team_search_context():
    assert '2026.09.09-573-YOUTH-KIT-SEARCH-INFO-CLASHES' in VERSION
    assert 'P2014' in KIT and 'U13' in KIT and 'truppsuffix' in KIT
    assert 'location=' in KIT and 'country_code=' in KIT and 'age_class=' in KIT and 'search_hint=' in KIT
    assert 'Sökledtråd (valfritt)' in APP

def test_partial_grounded_kit_results_are_supported_without_guessing():
    assert 'home_verified' in KIT and 'away_verified' in KIT
    assert 'bool(sources)' in KIT
    assert 'Hemma ej verifierat' in APP and 'Borta ej verifierat' in APP

def test_color_clashes_are_information_only():
    assert '"needs_action": False' in GUIDE
    assert 'möjliga färgkrockar · info' in WORK
    assert 'blockerar aldrig schema eller publicering' in WORK
    assert 'issues.append("Färgkrock")' not in WORK
