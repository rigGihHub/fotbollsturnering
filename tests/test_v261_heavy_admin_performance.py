from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
SCHEDULE_VIEW=(ROOT/"cupnavi_core"/"schedule_workspace_view.py").read_text(encoding="utf-8")
RESULTS_VIEW=(ROOT/"cupnavi_core"/"admin_results_view.py").read_text(encoding="utf-8")
RESULTS_REPO=(ROOT/"cupnavi_core"/"admin_results_repository.py").read_text(encoding="utf-8")


def _block(start_marker, end_marker):
    start=APP.index(start_marker)
    end=APP.index(end_marker,start)
    return APP[start:end]


def test_schedule_quality_analysis_is_genuinely_lazy():
    block=SCHEDULE_VIEW
    toggle=block.index('_show_schedule_quality = st.toggle(')
    gate=block.index('if _show_schedule_quality:', toggle)
    score=block.index('schedule_score_report(tid,rules)', gate)
    assert toggle < gate < score
    assert 'with st.expander("Regelverk & schemakvalitet", expanded=False)' not in block


def test_schedule_status_counts_are_batched_and_group_size_is_in_memory():
    block=SCHEDULE_VIEW
    assert 'AS group_match_n' in block
    assert 'AS unscheduled_group_n' in block
    assert 'AS scheduled_n' in block
    assert 'AS unpublished_n' in block
    assert 'AS played_n' in block
    assert '_schedule_team_counts' in block
    assert 'SELECT COUNT(*) AS n FROM teams WHERE group_id=?' not in block


def test_schedule_pdf_and_travel_are_lazy():
    block=SCHEDULE_VIEW
    assert '_show_schedule_export = st.toggle("Exportera schema"' in block
    assert 'if _show_schedule_export:' in block
    assert '_show_schedule_travel = st.toggle("Reseinformation"' in block
    assert 'if _show_schedule_travel:' in block


def test_results_reuse_loaded_matches_for_progress_and_focus():
    block=RESULTS_VIEW
    assert 'match_by_id = {int(row["id"]): row for row in matches}' in block
    assert 'total = len(matches)' in block
    assert 'played = sum(' in block
    assert 'SELECT COUNT(*) AS total' not in RESULTS_REPO
    assert 'SELECT * FROM matches WHERE tournament_id=? AND id=?' not in RESULTS_REPO


def test_results_full_schedule_is_lazy():
    block=RESULTS_VIEW
    gate=block.index('if show_full_result_schedule:')
    rows=block.index('all_match_rows = []',gate)
    assert gate < rows


def test_roster_widget_formatters_use_lookup_maps():
    block=_block('if admin_page == "Trupper":','if admin_page == "Domare":')
    assert '_team_name_by_id = {int(row["id"]): row["name"] for row in teams}' in block
    assert 'format_func=lambda x: _team_name_by_id.get(int(x), "Okänt lag")' in block
    assert '_player_by_id = {int(row["id"]): row for row in players}' in block
