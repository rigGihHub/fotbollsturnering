from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
STATS=(ROOT/"cupnavi_core/public_statistics_view.py").read_text(encoding="utf-8")

def test_statistics_view_is_extracted():
    assert "def render_public_statistics_section(" in STATS
    assert "calculate_all_group_tables(" in STATS
    assert "FROM player_match_stats" in STATS
    assert "render_bracket_tree(" in STATS

def test_app_keeps_thin_statistics_adapter_inside_outer_public_fragment():
    start=APP.index("def render_public_statistics_section")
    end=APP.index("def render_public_info_section", start)
    block=APP[start:end]
    assert "render_public_statistics_section_module(" in block
    assert len(block.splitlines()) < 35
