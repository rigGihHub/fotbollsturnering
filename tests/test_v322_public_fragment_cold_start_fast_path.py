from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "cupnavi_core" / "public_workspace_view.py").read_text(encoding="utf-8")
TEAM = (ROOT / "cupnavi_core" / "public_team_follow_view.py").read_text(encoding="utf-8")
MATCHES = (ROOT / "cupnavi_core" / "public_matches_view.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()


def test_v322_version():
    assert VERSION == "2026.08.31-351-SETUP-COMPLETION-HANDOFF"


def test_public_workspace_is_one_outer_fragment_without_nested_public_adapters():
    assert "@st.fragment\ndef render_public_view" in APP
    assert "@st.fragment\ndef render_public_statistics_section" not in APP
    assert "@st.fragment\ndef render_public_info_section" not in APP
    assert "@st.fragment\n        def render_public_matches_fragment" not in WORKSPACE


def test_public_explicit_reruns_stay_in_fragment():
    assert "st.rerun()" not in TEAM
    assert 'st.rerun(scope="fragment")' in TEAM
    assert "st.rerun()" not in MATCHES
    assert 'st.rerun(scope="fragment")' in MATCHES


def test_favorite_matches_uses_current_public_state_and_url():
    assert 'public_page_v167_' in TEAM
    assert 'public_page_v92_' not in TEAM
    assert 'st.query_params["section"] = "matches"' in TEAM


def test_cold_start_schema_fast_path_is_guarded_and_falls_back():
    assert "def _schema_fast_path_ready(con):" in APP
    assert "LATEST_SCHEMA_VERSION" in APP
    assert "except Exception:\n        return False" in APP[APP.index('def _schema_fast_path_ready'):APP.index('@st.cache_resource', APP.index('def _schema_fast_path_ready'))]
    assert "pragma_table_info('notification_subscriptions')" in APP
    assert "pragma_table_info('competition_classes')" in APP
    init_start = APP.index("def init_db():")
    execute_start = APP.index("execute_script(", init_start)
    fast_start = APP.index("if _schema_fast_path_ready(con):", init_start)
    assert fast_start < execute_start
    assert "return schema_key" in APP[fast_start:execute_start]
