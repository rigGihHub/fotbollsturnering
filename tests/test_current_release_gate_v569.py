from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "app.py"
TEXT = APP.read_text(encoding="utf-8")


def test_prepare_and_cupday_are_explicit_work_modes():
    assert "Arbetsläge" in TEXT
    assert "🧭 Förbered cupen" in TEXT
    assert "⚡ Cupdagen" in TEXT
    assert '_CUPDAY_OPERATIONAL_PAGES' in TEXT


def test_prepare_mode_returns_to_decision_driven_overview():
    assert 'def _open_prepare_mode()' in TEXT
    assert '_set_admin_page("Adminöversikt")' in TEXT


def test_cupday_mode_routes_to_operational_dashboard():
    assert 'def _open_cupday_mode()' in TEXT
    assert '_set_admin_page("Cupdagen")' in TEXT
    assert 'Operativt läge · Matchdag' in TEXT


def test_live_cup_explains_operational_priority_without_hiding_setup():
    assert 'Cupen är live · Cupdagen är det operativa arbetsläget' in TEXT
    assert 'Setup finns kvar' in TEXT
    # The full nine-step setup journey must survive the mode separation.
    for label in ["Cupinfo", "Lag", "Grupper", "Regler", "Planer & tider", "Domare", "Schema", "Kontroll", "Publicera"]:
        assert f'("{label}",' in TEXT
