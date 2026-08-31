from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = (ROOT / "cupnavi_core" / "match_reporter_workspace_view.py").read_text()
VERSION = "2026.08.31-353-GROUP-FLOW-PITCH-TIMING"


def test_version_markers_are_current():
    assert (ROOT / "VERSION.txt").read_text().strip() == VERSION
    assert VERSION in (ROOT / "app.py").read_text()
    assert VERSION in (ROOT / "cupnavi_core" / "version.py").read_text()


def test_queue_prioritizes_unreported_without_hiding_reported():
    block = WORKSPACE.split("def _reporter_match_queue", 1)[1].split("def _reporter_queue_label", 1)[0]
    assert "unreported + reported" in block
    assert "not _match_has_saved_result(row)" in block
    assert "_match_has_saved_result(row)" in block


def test_queue_labels_expose_next_unreported_and_reported_states():
    block = WORKSPACE.split("def _reporter_queue_label", 1)[1].split("def _next_unreported_match_id", 1)[0]
    assert 'status = "▶ Nästa"' in block
    assert 'status = "○ Orapporterad"' in block
    assert 'status = "✓ Rapporterad"' in block
    assert "match_result_label(match_row)" in block


def test_score_workspace_defaults_to_next_work_item_and_shows_counts():
    assert 'st.caption(\n                f"Matchkö · {len(unreported_ids)} orapporterade · "' in WORKSPACE
    assert "st.session_state[quick_score_widget_key] = next_unreported_id or queue_ids[0]" in WORKSPACE
    assert '"Alla spelbara matcher har ett sparat resultat."' in WORKSPACE
    assert "queue_ids" in WORKSPACE
    assert "_reporter_queue_label(" in WORKSPACE


def test_queue_is_navigation_only_and_existing_write_paths_remain():
    queue_block = WORKSPACE.split("def _reporter_match_queue", 1)[1].split("def _next_unreported_match_id", 1)[0]
    for forbidden in ("query_all(", "UPDATE ", "INSERT ", "DELETE ", "commit("):
        assert forbidden not in queue_block
    assert "save_quick_result" in WORKSPACE
    assert "save_event_rows" in WORKSPACE
    assert '"↩️ Ångra senaste"' in WORKSPACE
