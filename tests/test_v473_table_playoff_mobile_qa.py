from pathlib import Path

VERSION = "2026.09.07-519-BEGINNER-E2E-REGRESSION"
APP = Path("app.py").read_text(encoding="utf-8")
STATS = Path("cupnavi_core/public_statistics_view.py").read_text(encoding="utf-8")
PRESENT = Path("cupnavi_core/public_presentation_view.py").read_text(encoding="utf-8")


def test_version_is_v473():
    assert VERSION in APP
    assert Path("VERSION.txt").read_text().strip() == VERSION


def test_multiple_groups_are_visible_by_default():
    assert 'st.caption(f"{len(groups)} grupper · alla tabeller visas")' in STATS
    assert "expanded=True" in STATS
    assert 'f"{group[\'name\']} · {len(group_table)} lag"' in STATS


def test_single_group_keeps_simple_heading():
    assert 'if len(groups) == 1:' in STATS
    assert 'st.subheader(group["name"])' in STATS


def test_multiple_playoffs_are_visually_collapsed():
    assert 'st.caption(f"{len(brackets)} slutspel · första trädet är öppet")' in STATS
    assert "expanded=_bracket_index == 0" in STATS
    assert "render_bracket_tree(" in STATS


def test_mobile_table_density_handles_long_team_names():
    assert ".texttv-table td.team{{font-size:12px!important" in PRESENT
    assert "text-overflow:ellipsis" in PRESENT
    assert ".texttv-table th,.texttv-table td{{height:38px}}" in PRESENT


def test_no_domain_logic_changed():
    assert "calculate_all_group_tables(tournament_id, tournament)" in STATS
    assert "brackets_for_display(tournament_id)" in STATS
