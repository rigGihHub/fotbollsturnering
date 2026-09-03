from pathlib import Path

from cupnavi_core.public_view_logic import (
    PUBLIC_PAGE_SPECS,
    public_navigation_specs,
    resolve_public_page,
)

ROOT=Path(__file__).resolve().parents[1]
WORKSPACE=(ROOT/"cupnavi_core/public_workspace_view.py").read_text(encoding="utf-8")
VERSION=(ROOT/"VERSION.txt").read_text().strip()

def test_release_version():
    assert VERSION=="2026.09.03-424-PUBLIC-INFO-ROUNDTRIP-CUT"

def test_primary_public_navigation_matches_user_tasks():
    assert [row[0] for row in PUBLIC_PAGE_SPECS] == [
        "Info", "Matcher", "Mitt lag", "Tabeller", "Slutspel"
    ]
    assert [row[2] for row in public_navigation_specs()] == [
        "Info", "Matcher", "Mitt lag", "Tabell", "Slutspel"
    ]
    assert all(row[0] != "Statistik" for row in PUBLIC_PAGE_SPECS)

def test_mitt_lag_is_a_real_route():
    assert resolve_public_page("team") == "Mitt lag"
    assert 'if public_page == "Mitt lag":' in WORKSPACE
    assert 'or public_page in {"Matcher", "Mitt lag"}' in WORKSPACE

def test_team_follow_is_not_rendered_globally_anymore():
    team_route = WORKSPACE.index('if public_page == "Mitt lag":')
    follow = WORKSPACE.index("render_public_team_follow(", team_route)
    matches_route = WORKSPACE.index('if public_page == "Matcher":')
    assert team_route < follow < matches_route
    assert WORKSPACE.count("render_public_team_follow(") == 1

def test_toplists_are_secondary_under_tables():
    # v390 keeps v386's IA decision (no top-level Statistik tab) but upgrades
    # the buried toggle to a visible secondary segmented choice under Tabell.
    assert '[tr("Tabeller"), tr("Topplistor")]' in WORKSPACE
    assert 'public_competition_view_' in WORKSPACE
    assert 'forced_section=tr("Topplistor")' in WORKSPACE
    assert 'if public_page == "Statistik":' not in WORKSPACE

def test_old_stats_deep_links_degrade_to_tables():
    assert resolve_public_page("stats") == "Tabeller"
