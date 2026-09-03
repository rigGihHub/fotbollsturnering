from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
RESULTS=(ROOT/"cupnavi_core/admin_results_view.py").read_text(encoding="utf-8")
REPO=(ROOT/"cupnavi_core/admin_results_repository.py").read_text(encoding="utf-8")
VERSION=(ROOT/"VERSION.txt").read_text().strip()

def _groups():
    start=APP.index('if admin_page == "Grupper":')
    end=APP.index('if admin_page == "Trupper":', start)
    return APP[start:end]

def test_release_version():
    assert VERSION=="2026.09.03-424-PUBLIC-INFO-ROUNDTRIP-CUT"

def test_manual_group_tools_are_true_lazy():
    block=_groups()
    assert 'key=f"lazy_manual_groups_{tid}"' in block
    assert 'key=f"lazy_edit_groups_{tid}"' in block
    assert 'with st.expander("Skapa grupper själv"' not in block
    assert 'with st.expander("Redigera eller ta bort grupp")' not in block

def test_group_readiness_reuses_loaded_rows():
    block=_groups()
    assert "_groups_after_assignment = groups" in block
    assert '_unassigned_after_assignment = sum(1 for team_row in teams if team_row["group_id"] is None)' in block
    assert '_groups_after_assignment = all_rows("SELECT id FROM groups WHERE tournament_id=?", (tid,))' not in block
    assert 'SELECT COUNT(*) AS n FROM teams WHERE tournament_id=? AND group_id IS NULL' not in block

def test_results_load_matches_before_auxiliary_data():
    assert "def fetch_admin_results_matches(" in REPO
    assert "def fetch_admin_results_auxiliary(" in REPO
    match_load=RESULTS.index("matches = fetch_admin_results_matches(")
    playable=RESULTS.index("if not playable_matches:")
    aux=RESULTS.index("refs, all_result_teams = fetch_admin_results_auxiliary(")
    assert match_load < playable < aux

def test_compatibility_repository_remains_available():
    assert "def fetch_admin_results_data(" in REPO
    assert "fetch_admin_results_matches(all_rows, tournament_id)" in REPO
    assert "fetch_admin_results_auxiliary(all_rows, tournament_id)" in REPO
