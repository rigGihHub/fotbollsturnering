from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
app=(ROOT/"app.py").read_text(encoding="utf-8")
public_workspace=(ROOT/"cupnavi_core/public_workspace_view.py").read_text(encoding="utf-8")
public_matches=(ROOT/"cupnavi_core/public_matches_view.py").read_text(encoding="utf-8")
public_team_follow=(ROOT/"cupnavi_core/public_team_follow_view.py").read_text(encoding="utf-8")
repo=(ROOT/"cupnavi_api/repository.py").read_text(encoding="utf-8")
main=(ROOT/"cupnavi_api/main.py").read_text(encoding="utf-8")
match_reporter=(ROOT/"cupnavi_core/match_reporter_workspace_view.py").read_text(encoding="utf-8")
wizard=(ROOT/"cupnavi_core/new_tournament_wizard.py").read_text(encoding="utf-8")
initial_setup=(ROOT/"cupnavi_core/initial_setup_view.py").read_text(encoding="utf-8")
performance_module=(ROOT/"cupnavi_core/performance.py").read_text(encoding="utf-8")
assert "def public_core_snapshot" in app
assert "_public_core = public_core_snapshot(" in public_workspace
assert "include_matches=_needs_public_matches" in public_workspace
assert "def public_snapshot" in repo and "with connect() as con:" in repo[repo.index("def public_snapshot"):]
assert "Server-Timing" in main and "X-CupNavi-Process-Ms" in main
assert "on_click=_adjust_quick_score" in match_reporter
assert "on_click=_save_quick_result_callback" in match_reporter
assert "on_click=_set_match_status_callback" in match_reporter
assert "on_click=_clear_public_search" in public_workspace
assert "on_click=_open_public_search_result" in public_workspace
assert "on_click=_clear_public_team_filter" in public_matches
assert "on_click=_show_more_public_matches" in public_matches
assert "on_change=_sync_public_favorite_team" in public_team_follow
assert "on_click=_open_public_team_matches" in public_team_follow
assert "on_click=_clear_public_favorite_team" in public_team_follow
assert "on_click=_open_public_next_match" in public_team_follow
assert "favorite_team_primary_action_label" in public_team_follow
assert "if show_directions:" in public_team_follow
assert "if show_match_events and visible_played_match_ids" in public_matches
assert "def public_scorer_leader_db_snapshot" in app
assert "public_scorer_leader_db_snapshot=public_scorer_leader_db_snapshot" in app
assert "load_overview=public_scorer_leader_db_snapshot" in public_workspace
assert "on_click=_set_wizard_step" in wizard
assert "on_click=_leave_rules_for_step" in initial_setup
assert "on_click=_open_admin_page" in app
assert "_cupnavi_admin_cache_flow_primary_" in app
assert "_cupnavi_admin_cache_sidebar_rules_" in app
assert "_cupnavi_admin_cache_lifecycle_counts_" in app
assert "PERFORMANCE_BUDGETS" in performance_module
for _route in (
    "Turneringsvy/Info",
    "Turneringsvy/Matcher",
    "Turneringsvy/Mitt lag",
    "Admin/Adminöversikt",
    "Admin/Lag",
    "Admin/Grupper",
    "Admin/Skapa och publicera schema",
    "Admin/Kontroller",
):
    assert f'"{_route}"' in performance_module
assert '"Budget": (' in app

# v448: mobile playoff must stay an in-memory presentation pass.
_public_presentation = (ROOT / "cupnavi_core" / "public_presentation_view.py").read_text()
_mobile_start = _public_presentation.index("def _mobile_status")
_mobile_end = _public_presentation.index("bronze_matches =", _mobile_start)
_mobile_block = _public_presentation[_mobile_start:_mobile_end]
assert "all_rows(" not in _mobile_block, "Mobile playoff must not add DB roundtrips"
assert "one_row(" not in _mobile_block, "Mobile playoff must not add DB roundtrips"
assert "Vinnaren går vidare till" in _mobile_block, "Mobile playoff progression path missing"

print("Performance contract OK")
