from pathlib import Path
APP=(Path(__file__).resolve().parents[1]/"app.py").read_text(encoding="utf-8")


def test_publish_control_exists_in_main_content_not_only_sidebar():
    assert '📣 Publicera / uppdatera publik vy' in APP
    assert 'mobile_publish_from_admin_' in APP
    assert '_publish_tournament_now()' in APP


def test_mobile_publish_uses_same_blocker_state():
    block=APP[APP.index('# v159: Publicering'):APP.index('# Cupens livscykel')]
    assert 'disabled=sidebar_publish_blocked' in block
    assert 'publish_blockers' in block


def test_publishing_marks_all_scheduled_matches_public():
    block=APP[APP.index('def _publish_tournament_now'):APP.index('def _unpublish_tournament_now')]
    assert 'UPDATE matches SET schedule_published=1' in block
    assert 'scheduled_start IS NOT NULL' in block
    assert 'UPDATE tournaments SET is_published=1' in block


def test_admin_result_autosave_repairs_public_match_flag_when_cup_is_published():
    page=APP[APP.index('if admin_page == "Matcher och resultat"'):APP.index('if admin_page == "Matchhändelser"')]
    assert 'if tournament["is_published"]:' in page
    assert 'UPDATE matches SET schedule_published=1 WHERE id=? AND scheduled_start IS NOT NULL' in page


def test_public_view_reads_scores_directly_from_published_match_rows():
    core=APP[APP.index('def public_core_snapshot'):APP.index('def run_many')]
    public=APP[APP.index('def render_public_view'):APP.index('def render_match_reporter_view')]
    assert 'schedule_published=1' in core
    assert '_public_core = public_core_snapshot(tournament_id)' in public
    assert 'played_matches = [m for m in published_matches if m["home_score"] is not None and m["away_score"] is not None]' in public


def test_draft_admin_explains_saved_results_are_not_public_yet():
    assert 'Resultaten är sparade men cupen är inte publicerad ännu.' in APP
    assert 'sparade resultat slår igenom automatiskt i turneringsvyn' in APP
