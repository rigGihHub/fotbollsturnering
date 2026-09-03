from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "cupnavi_core" / "match_reporter_workspace_view.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()


def _function_source(source: str, name: str) -> str:
    tree = ast.parse(source)
    lines = source.splitlines()
    node = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name)
    return "\n".join(lines[node.lineno - 1: node.end_lineno])


def test_workspace_owns_reporter_streamlit_orchestration():
    assert "def render_match_reporter_workspace(" in WORKSPACE
    assert 'st.segmented_control(' in WORKSPACE
    assert 'reporter_workspace_section_' in WORKSPACE
    assert 'quick_score_widget_key = f"quick_score_match_{tournament_id}"' in WORKSPACE
    assert 'key=quick_score_widget_key' in WORKSPACE
    assert 'key=f"reporter_results_{tournament_id}"' in WORKSPACE
    assert 'key=f"reporter_stats_{match_id}_{selected_team_id}"' in WORKSPACE
    assert "build_offline_draft_html" in WORKSPACE


def test_app_reporter_entrypoint_is_thin_dependency_boundary():
    fn = _function_source(APP, "render_match_reporter_view")
    assert "render_match_reporter_workspace(" in fn
    assert "MatchReporterWorkspaceDeps(" in fn
    assert "st.data_editor(" not in fn
    assert "st.selectbox(" not in fn
    assert "with db()" not in fn


def test_protected_writes_remain_in_app_callbacks_not_workspace():
    assert "update_match_result_if_unchanged(" in _function_source(APP, "_reporter_save_quick_result")
    assert "update_match_result_if_unchanged(" in _function_source(APP, "_reporter_save_bulk_results")
    assert "update_player_match_stats_if_unchanged(" in _function_source(APP, "_reporter_save_event_rows")
    assert "INSERT INTO referee_acknowledgements" in _function_source(APP, "_reporter_acknowledge_referee")
    assert "update_match_result_if_unchanged(" not in WORKSPACE
    assert "update_player_match_stats_if_unchanged(" not in WORKSPACE
    assert "INSERT INTO referee_acknowledgements" not in WORKSPACE


def test_workspace_uses_injected_persistence_callbacks():
    assert "deps.save_quick_result(" in WORKSPACE
    assert "deps.save_bulk_results(" in WORKSPACE
    assert "deps.save_event_rows(" in WORKSPACE
    assert "deps.acknowledge_referee(" in WORKSPACE


def test_release_version():
    assert VERSION == "2026.09.03-423-PUBLIC-INFO-COLD-START"
