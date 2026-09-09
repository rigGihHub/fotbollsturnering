from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
VERSION = "2026.09.09-591-RULES-FLOW-UX-PASS"

def test_release_identity():
    assert (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip() == VERSION
    assert VERSION in APP
    assert VERSION in (ROOT / "cupnavi_core/version.py").read_text(encoding="utf-8")

def test_rules_flow_is_novice_first():
    assert "### 1. Bestäm det viktigaste" in APP
    assert "För de flesta cuper räcker det att kontrollera matchtid och poäng här." in APP
    assert "#### Matchtid" in APP
    assert "#### Poäng" in APP
    assert "⚙️ Fler regler · tabell, slutspel och schemaprinciper" in APP

def test_rules_flow_has_single_forward_cta_after_form():
    block = APP[APP.index('if admin_page == "Regler":'):APP.index('if admin_page == "Cupinställningar":')]
    assert block.count('Fortsätt till Planer & tider →') == 1
    assert block.index('Spara regler') < block.index('Fortsätt till Planer & tider →')
    assert '📦 Regler från första importen' in block
    assert 'inget skrivs över utan ditt val' in block
