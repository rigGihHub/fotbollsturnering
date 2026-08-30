from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SCRIPT=(ROOT/"scripts/check_performance_contract.py").read_text(encoding="utf-8")
WORKSPACE=(ROOT/"cupnavi_core/public_workspace_view.py").read_text(encoding="utf-8")
def test_contract_tracks_workspace():
    assert 'assert "_public_core = public_core_snapshot(" in public_workspace' in SCRIPT
    assert '_public_core = public_core_snapshot(' in WORKSPACE
    assert 'include_matches=_needs_public_matches' in WORKSPACE
def test_release_version():
    assert (ROOT/"VERSION.txt").read_text(encoding="utf-8").strip()=="2026.08.30-320-PUBLIC-PLAYOFF-TEAM-BATCHING"
