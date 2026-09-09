from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
AI=(ROOT/'cupnavi_core'/'ai_cup_document_import.py').read_text(encoding='utf-8')
VIEW=(ROOT/'cupnavi_core'/'cup_document_creator_view.py').read_text(encoding='utf-8')
APP=(ROOT/'app.py').read_text(encoding='utf-8')

def test_v499_version_and_complete_document_schema():
    assert '2026.09.07-525-OPTIONAL-REFEREE-SETUP' in APP
    for field in ("'matches'", "'playoff_matches'", "'rules'", "'duration'"):
        assert field in AI

def test_review_shows_schedule_playoff_and_does_not_auto_write_matches():
    assert 'Matchprogram som CupNavi hittade' in VIEW
    assert 'Slutspel som CupNavi hittade' in VIEW
    assert 'Regler och praktiska uppgifter som hittades' in VIEW
    assert 'skrivs inte automatiskt till spelschemat' in VIEW
    assert 'uttryckliga godkännande' in VIEW
