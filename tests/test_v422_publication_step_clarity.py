from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIEW = (ROOT / "cupnavi_core" / "admin_publication_view.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()


def test_v422_version_and_final_step_label():
    assert VERSION == "2026.09.03-424-PUBLIC-INFO-ROUNDTRIP-CUT"
    assert "Steg 6 av 6 · Publicera" in VIEW
    assert "Steg 5 av 5 · Publicera" not in VIEW


def test_v422_publication_card_does_not_repeat_control_dashboard():
    main = VIEW.split("if not show_main_control:", 1)[1]
    assert 'st.success("✓ Kontroll klar – cupen är redo att publiceras")' in main
    assert 'q1.metric("Kritiska fel"' not in main
    assert 'q2.metric("Varningar"' not in main
    assert 'q3.metric("Förbättringar"' not in main
