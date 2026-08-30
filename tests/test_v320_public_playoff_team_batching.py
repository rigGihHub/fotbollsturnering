from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRESENTATION = (ROOT / "cupnavi_core" / "public_presentation_view.py").read_text()
STATS = (ROOT / "cupnavi_core" / "public_statistics_view.py").read_text()
WORKSPACE = (ROOT / "cupnavi_core" / "public_workspace_view.py").read_text()
APP = (ROOT / "app.py").read_text()
VERSION = (ROOT / "VERSION.txt").read_text().strip()

def test_v320_version():
    assert VERSION == "2026.08.30-320-PUBLIC-PLAYOFF-TEAM-BATCHING"

def test_public_workspace_passes_existing_team_map_to_statistics():
    assert "public_team_by_id=public_team_by_id" in WORKSPACE

def test_statistics_passes_team_map_to_each_public_bracket():
    assert 'render_bracket_tree(bracket["id"], public=True, team_by_id=public_team_by_id)' in STATS

def test_bracket_renderer_reuses_injected_teams_before_fallback_query():
    injected = PRESENTATION.index("bracket_team_by_id = {int(key): row for key, row in (team_by_id or {}).items()}")
    guard = PRESENTATION.index("if not bracket_team_by_id and bracket_matches:", injected)
    query = PRESENTATION.index("SELECT id,name,primary_color,secondary_color FROM teams", guard)
    assert injected < guard < query

def test_admin_adapter_keeps_database_fallback_optional():
    assert "def render_bracket_tree(bracket_id, public=False, *, team_by_id=None):" in APP
    assert "team_by_id=team_by_id" in APP
