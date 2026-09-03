from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIEW = (ROOT / "cupnavi_core" / "new_tournament_wizard.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()


def test_v417_version():
    assert VERSION == "2026.09.03-423-PUBLIC-INFO-COLD-START"


def test_manual_setup_is_primary_path_for_tournaments():
    assert 'st.markdown("### Bestäm upplägget")' in VIEW
    assert '"Ställ in regler och upplägg själv"' in VIEW
    assert 'type="primary"' in VIEW
    assert 'st.session_state["new_tournament_setup_mode"] = "edit"' in VIEW


def test_cupnavi_recommendation_is_explicitly_secondary_and_optional():
    assert 'CupNavi kan ge ett snabbförslag, men det är alltid frivilligt.' in VIEW
    assert '"Använd CupNavis snabbförslag"' in VIEW
    # The recommendation button must no longer be the primary CTA.
    line = next(line for line in VIEW.splitlines() if '"Använd CupNavis snabbförslag"' in line)
    assert 'type="primary"' not in line
