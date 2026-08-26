from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
E2E = (ROOT / "e2e/test_streamlit_critical_journey.py").read_text(encoding="utf-8")

def test_streamlit_render_path_has_no_ci_autocomplete_mutation():
    assert "e2e_autocomplete_done_" not in APP
    assert "E2E auto-completion failed:" not in APP

def test_browser_journey_uses_deterministic_fixture():
    assert "def seed_completed_cup_fixture(" in E2E
    assert "seed_completed_cup_fixture(tid)" in E2E
    assert "wait_for_e2e_auto_completion" not in E2E

def test_clean_nav_role_transition_is_reflected_in_e2e():
    block = E2E[E2E.index("# 5. Role boundary"):E2E.index("# 6. Mobile public verification")]
    assert 'name="Admin"' in block
    assert 'name="Matchrapportör"' in block
