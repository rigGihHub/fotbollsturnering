from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = (ROOT / "frontend-next/src/components/admin-workspace.tsx").read_text()


def test_cup_selector_labels_publication_state_and_warns_about_duplicate_draft():
    assert 'cup.is_published?"PUBLICERAD":"UTKAST"' in WORKSPACE
    assert "publishedTwin" in WORKSPACE
    assert "LIKANDE CUP FINNS REDAN LIVE" in WORKSPACE
    assert "Öppna publicerad cup →" in WORKSPACE


def test_tournament_keeps_playoff_admin_reachable():
    assert 'if(isMatchcamp)return href!=="#groups"&&href!=="#playoffs"' in WORKSPACE
    assert 'if(cupinfo?.arrangement_type==="tournament")return href!=="#playoffs"' not in WORKSPACE
