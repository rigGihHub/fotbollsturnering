from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SETUP = (ROOT / "cupnavi_core" / "initial_setup_view.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()


def test_v340_version_marker():
    assert VERSION == "2026.09.04-449-MOBILE-PLAYOFF-ACTION"


def test_standard_setup_is_three_step_fast_track():
    assert "cn-setup-step done" in SETUP
    assert "Tävlingsklasser" in SETUP
    assert "Kapacitet" in SETUP
    assert "Lägg till lag" in SETUP
    assert "Fortsätt → Lägg till lag" in SETUP


def test_advanced_setup_is_explicitly_opt_in():
    toggle = SETUP.index('"Visa och ändra alla regler & format"')
    advanced = SETUP.index('st.markdown("### 3. Rekommenderat tävlingsformat")')
    assert toggle < advanced
    assert "if _show_advanced_setup:" in SETUP
    assert "Här kan du alltid se och ändra CupNavis förslag" in SETUP


def test_advanced_capabilities_are_retained():
    for marker in (
        "### 3. Rekommenderat tävlingsformat",
        "### 4. Tävlingsregler",
        "### 4. Matchregler och hårda begränsningar",
        "### 5. Vad är viktigast i schemat?",
        "### 6. Arrangemang & deltagarservice",
        "### 7. Redo att fortsätta",
        "Valfria statistik- och driftfunktioner",
    ):
        assert marker in SETUP


def test_no_database_or_schedule_rewrite_is_introduced_by_v340_gate():
    gate_start = SETUP.index("_show_advanced_setup = st.toggle")
    gate_end = SETUP.index('notice=st.session_state.pop', gate_start)
    gated = SETUP[gate_start:gate_end]
    assert "DROP TABLE" not in gated
    assert "ALTER TABLE" not in gated
    assert "generate_schedule(" not in gated
