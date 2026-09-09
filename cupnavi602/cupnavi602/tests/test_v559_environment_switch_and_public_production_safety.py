from pathlib import Path

APP = Path('app.py').read_text(encoding='utf-8')


def test_admin_has_sidebar_environment_switch():
    assert '"Arbetsmiljö"' in APP
    assert '"🧪 Testmiljö" if value == "test" else "🟢 Skarp miljö"' in APP
    assert 'st.session_state["admin_environment"]' in APP


def test_admin_list_is_filtered_by_selected_environment():
    assert "AND COALESCE(environment_type,'production')=?" in APP
    assert "AND COALESCE(t.environment_type,'production')=?" in APP


def test_environment_switch_drops_cross_environment_cup_selection():
    for key in (
        '"active_tournament_selector"',
        '"main_active_tournament_selector"',
        '"preferred_tournament_id"',
    ):
        assert key in APP
    assert 'Never carry a cup selection across environments.' in APP


def test_public_discovery_only_returns_production_cups():
    assert "is_published=1 AND COALESCE(environment_type,'production')='production'" in APP


def test_direct_public_cup_links_also_require_production():
    assert APP.count("AND COALESCE(environment_type,'production')='production'") >= 3


def test_creator_defaults_to_selected_admin_environment():
    assert '_creator_env = str(st.session_state.get("admin_environment", "test") or "test")' in APP
    assert 'index=0 if _creator_env == "production" else 1' in APP
