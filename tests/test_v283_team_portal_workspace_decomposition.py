from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
VIEW = (ROOT / "cupnavi_core" / "team_portal_view.py").read_text(encoding="utf-8")
REPO = (ROOT / "cupnavi_core" / "team_portal_repository.py").read_text(encoding="utf-8")


def test_app_team_portal_is_thin_dependency_boundary():
    start = APP.index("def render_team_portal(")
    end = APP.index("\n\n\ninit_db()", start)
    block = APP[start:end]
    assert "TeamPortalDependencies(" in block
    assert "render_team_portal_workspace(" in block
    assert "st.form(" not in block
    assert "SELECT * FROM teams" not in block


def test_workspace_owns_portal_ui_but_not_sensitive_writer_definitions():
    for marker in (
        'st.tabs(["Lag & matcher", "Trupp", "Matchtrupper", message_tab_label])',
        '"Spara matchtrupp"',
        '"Kopiera föregående matchtrupp"',
        '"Skicka meddelande"',
        '"Bekräfta matchställ"',
    ):
        assert marker in VIEW
    for writer in (
        "def _set_team_checkin_if_unchanged",
        "def _confirm_team_kit_if_unchanged",
        "def _save_team_contact_if_unchanged",
        "def _save_match_roster_if_unchanged",
        "def _update_team_player_if_unchanged",
        "def _delete_team_player_if_unchanged",
    ):
        assert writer not in VIEW
        assert writer in APP


def test_repository_owns_read_only_portal_queries():
    assert "SELECT * FROM teams WHERE tournament_id=?" in REPO
    assert "participant_access_credentials" in REPO
    assert "FROM team_messages" in REPO
    assert "FROM match_rosters" in REPO
    assert "FROM matches" in REPO
    assert "INSERT " not in REPO
    assert "UPDATE " not in REPO
    assert "DELETE " not in REPO


def test_portal_match_reads_keep_source_resolution_filter():
    assert "home_source NOT LIKE 'team:%'" in REPO
    assert "away_source NOT LIKE 'team:%'" in REPO
    assert "match_team_ids(row)" in REPO
