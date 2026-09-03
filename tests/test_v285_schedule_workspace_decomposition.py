from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
VIEW = (ROOT / "cupnavi_core" / "schedule_workspace_view.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()
CORE_VERSION = (ROOT / "cupnavi_core" / "version.py").read_text(encoding="utf-8")


def test_v285_version_is_synchronized():
    expected = "2026.09.03-427-TRAVEL-RULES-FLOW"
    assert VERSION == expected
    assert f'APP_VERSION = "{expected}"' in CORE_VERSION
    assert f'APP_BUILD_VERSION = "{expected}"' in APP


def test_schedule_page_delegates_to_workspace_module():
    start = APP.index('if admin_page == "Skapa och publicera schema":')
    end = APP.index('if admin_page == "Matcher och resultat":', start)
    block = APP[start:end]
    assert "render_schedule_workspace(" in block
    assert "ScheduleWorkspaceDependencies(" in block
    assert '"Skapa hela spelschemat"' not in block
    assert '"Tillämpa drag-and-drop-ordningen"' not in block


def test_workspace_owns_schedule_ui_and_progressive_disclosure():
    for marker in (
        '"Visa regelverk & schemakvalitet"',
        'st.markdown("#### Skapa eller uppdatera schema")',
        '"Skapa hela spelschemat"',
        '"Uppdatera återstående schema"',
        'with st.expander("Detaljer per grupp", expanded=False)',
        '_show_schedule_export = st.toggle("Exportera schema"',
        '_show_schedule_travel = st.toggle("Reseinformation"',
        '"Tillämpa drag-and-drop-ordningen"',
        '"Spara alla resultat i schemat"',
    ):
        assert marker in VIEW


def test_persistence_sensitive_schedule_writes_stay_in_app_callbacks():
    for callback in (
        "def _undo_schedule_change(",
        "def _apply_drag_schedule_updates(",
        "def _save_adjusted_schedule_match(",
        "def _save_bulk_schedule_results(",
    ):
        assert callback in APP
    assert "with db() as con:" not in VIEW
    assert "_clear_render_query_cache()" not in VIEW
    assert "undo_schedule_change(tid, undo_rows)" in VIEW
    assert "apply_drag_schedule_updates(tid, updates)" in VIEW
    assert "save_adjusted_schedule_match(" in VIEW
    assert "save_bulk_schedule_results(tid, changed_scores" in VIEW


def test_schedule_engine_stays_in_app_and_is_injected():
    assert "def generate_schedule(" in APP
    assert "def ensure_playoffs_for_schedule(" in APP
    assert "generate_schedule=generate_schedule" in APP
    assert "ensure_playoffs_for_schedule=ensure_playoffs_for_schedule" in APP
    assert "generate_schedule(tid, tournament, rules" in VIEW


def test_app_monolith_is_smaller_than_v284():
    assert len(APP.splitlines()) < 16629
