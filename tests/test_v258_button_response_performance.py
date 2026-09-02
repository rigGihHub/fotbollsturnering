from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "app.py"
SOURCE = APP.read_text(encoding="utf-8")
SCHEDULE_VIEW = (APP.parent / "cupnavi_core" / "schedule_workspace_view.py").read_text(encoding="utf-8")


def test_flow_counts_only_load_for_primary_flow_pages():
    assert "_flow_counts = None" in SOURCE
    assert "if _flow_index is not None:" in SOURCE
    assert '_flow_counts = one_row(' in SOURCE
    assert "else:\n    _recommended_page = _recommended_label = None" in SOURCE


def test_checkin_audit_is_batched_in_same_transaction():
    start = SOURCE.index('if st.button("Spara incheckning"')
    end = SOURCE.index('if st.toggle("Lagportal – koder"', start)
    block = SOURCE[start:end]
    assert "changes = []" in block
    assert "INSERT INTO audit_log" in block
    assert "record_audit(" not in block
    assert block.count("with db() as con:") == 1


def test_bulk_result_save_skips_unchanged_matches_and_combines_publish_update():
    start = SCHEDULE_VIEW.index('if st.button("Spara alla resultat i schemat")')
    end = SCHEDULE_VIEW.index('st.caption("Målskyttar, assist', start)
    block = SCHEDULE_VIEW[start:end]
    assert "original_scores" in block
    assert "changed_scores" in block
    assert "if original_scores.get(match_id) != (home_score, away_score)" in block
    assert "save_bulk_schedule_results(tid, changed_scores" in block
    assert "schedule_published=CASE WHEN scheduled_start IS NOT NULL THEN 1 ELSE schedule_published END" in SOURCE


def test_group_save_only_updates_changed_assignments():
    start = SOURCE.index('if st.button("Spara gruppindelning"')
    end = SOURCE.index('else:\n        if tournament_age_classes:', start)
    block = SOURCE[start:end]
    assert "current_group_by_team" in block
    assert "group_changes" in block
    assert 'con.executemany("UPDATE teams SET group_id=? WHERE id=?", group_changes)' in block
