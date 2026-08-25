from pathlib import Path

APP = Path("app.py").read_text(encoding="utf-8")


def setup_block():
    start = APP.index("def render_initial_tournament_setup")
    end = APP.index("def _render_with_friendly_error", start)
    return APP[start:end]


def test_pitch_capacity_is_part_of_early_venue_constraints():
    block = setup_block()
    capacity = block.index("Antal tillgängliga planer/spelytor")
    windows = block.index("save_pitch_day_window")
    match_rules = block.index("### 5. Match- och schemaregler")
    assert capacity < windows < match_rules
    assert block.count("setup_pitches_{tournament_id}") == 1


def test_start_template_has_no_cupnavi_recommendation_panel():
    start = APP.index('with st.sidebar.expander("Skapa ny turnering")')
    end = APP.index('if view_mode == "Admin":\n    clone_sources', start)
    assert "CupNavi rekommenderar" not in APP[start:end]


def test_v132_version_is_synchronized_in_app():
    assert Path('VERSION.txt').read_text(encoding='utf-8').strip() in APP
