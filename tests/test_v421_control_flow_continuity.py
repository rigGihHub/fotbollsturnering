from pathlib import Path

from cupnavi_core.version import APP_VERSION

APP = Path("app.py").read_text(encoding="utf-8")


def test_v421_version():
    assert APP_VERSION == "2026.09.03-427-TRAVEL-RULES-FLOW"


def test_control_page_uses_shared_six_step_flow():
    assert '_control_flow_steps = ["Grundsetup", "Lag", "Grupper", "Schema", "Kontroll", "Publicera"]' in APP
    assert 'key=f"control_flow_back_to_schedule_{tid}"' in APP
    assert 'args=("Schema",)' in APP
    assert 'Nästa steg: Publicera nedan' in APP


def test_legacy_control_step_label_removed():
    assert '<div class="kicker">Steg 4 av 5 · Kontroll</div>' not in APP
