from pathlib import Path

from cupnavi_core.version import APP_VERSION

APP = Path("app.py").read_text(encoding="utf-8")


def test_v421_version():
    assert APP_VERSION == "2026.09.07-520-UNIQUE-PUBLICATION-CHECKLIST-KEYS"


def test_control_page_uses_shared_six_step_flow():
    assert 'render_clickable_planning_flow(st, tid=tid, current_step="Kontroll"' in APP
    assert 'Fortsätt till Publicera →' in APP

def test_legacy_control_step_label_removed():
    assert '<div class="kicker">Steg 4 av 5 · Kontroll</div>' not in APP
