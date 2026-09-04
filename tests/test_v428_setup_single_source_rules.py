from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SRC=(ROOT/"cupnavi_core"/"initial_setup_view.py").read_text(encoding="utf-8")
VERSION=(ROOT/"VERSION.txt").read_text().strip()

def test_v428_version():
    assert VERSION=="2026.09.04-449-MOBILE-PLAYOFF-ACTION"

def test_rules_block_does_not_reask_pitch_timing():
    block=SRC[SRC.index('# v428: manual setup'):SRC.index('# v364: Matchcamp')]
    assert 'checkbox("Kräv samma avsparkstider på alla planer"' not in block
    assert 'Plantidernas arbetssätt är redan satt till' in block
    assert 'Ändra planer & tider' in block

def test_rules_block_owns_playoff_rules_without_reasking_result_mode():
    block=SRC[SRC.index('# v428: manual setup'):SRC.index('# v364: Matchcamp')]
    assert '### Slutspel' in block
    assert 'Typ av slutspel' in block
    assert 'Bronsmatch' in block
    assert 'Oavgjord slutspelsmatch' in block
    assert 'Resultatläge' not in block
