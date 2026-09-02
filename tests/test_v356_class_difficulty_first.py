from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SETUP = (ROOT / "cupnavi_core" / "initial_setup_view.py").read_text(encoding="utf-8")
APP = (ROOT / "app.py").read_text(encoding="utf-8")

def test_difficulty_is_selected_before_class_is_added():
    assert 'setup_difficulty = st.selectbox(' in SETUP
    assert '"Svårighetsgrad"' in SETUP
    assert SETUP.index('setup_difficulty = st.selectbox(') < SETUP.index('setup_class_teams = st.number_input(')
    assert 'add_competition_class(tournament_id, setup_category, setup_year, setup_class_teams, setup_difficulty)' in SETUP

def test_new_class_persists_selected_difficulty():
    assert 'def add_competition_class(tournament_id, category, year, planned_team_count=0, difficulty="Medel"):' in APP
    assert 'SET planned_team_count=?, difficulty=?' in APP
