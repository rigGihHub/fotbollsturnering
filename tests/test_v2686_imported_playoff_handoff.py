from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = (ROOT / "frontend-next/src/components/cup-create-launcher-v6.tsx").read_text()
WORKSPACE = (ROOT / "frontend-next/src/components/admin-workspace.tsx").read_text()
SUMMARY = (ROOT / "frontend-next/src/components/import-completion-summary.tsx").read_text()


def test_new_import_hands_detected_playoffs_to_review():
    assert "playoffs:(proposal.playoff_matches||[]).length" in LAUNCHER
    assert 'goToCup(cup,(proposal.playoff_matches||[]).length?"playoffs":"overview")' in LAUNCHER
    assert "Granska slutspelet →" in WORKSPACE
    assert "slutspelsmatcher</span>" in WORKSPACE


def test_incomplete_import_summary_is_visible_and_actionable():
    assert "!summary.complete" not in SUMMARY.split("return null",1)[0]
    assert 'summary.pending?.includes("playoff_matches")' in SUMMARY
    assert "Granska och spara slutspelet →" in SUMMARY
    assert "Importen är inte färdig" in SUMMARY
