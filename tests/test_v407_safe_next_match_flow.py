from datetime import datetime
from pathlib import Path

from cupnavi_core.admin_results_view import safe_next_match_start_state

ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT / "VERSION.txt").read_text().strip()
RESULTS = (ROOT / "cupnavi_core" / "admin_results_view.py").read_text()
APP = (ROOT / "app.py").read_text()

def test_v408_version():
    assert VERSION == "2026.09.03-427-TRAVEL-RULES-FLOW"

def test_safe_start_window():
    row={"scheduled_start":"2026-09-03T10:00:00","match_status":"not_started"}
    assert safe_next_match_start_state(row, now=datetime(2026,9,3,9,50))["can_start"]
    assert not safe_next_match_start_state(row, now=datetime(2026,9,3,9,49))["can_start"]
    assert safe_next_match_start_state(row, now=datetime(2026,9,3,10,5))["can_start"]

def test_non_pending_match_never_direct_starts():
    row={"scheduled_start":"2026-09-03T10:00:00","match_status":"live"}
    assert not safe_next_match_start_state(row, now=datetime(2026,9,3,10,0))["can_start"]

def test_handoff_uses_existing_status_guard_and_no_query():
    block=RESULTS[RESULTS.index("def safe_next_match_start_state"):RESULTS.index("def prepare_admin_result_updates")]
    assert "deps.all_rows" not in block
    assert "early_start_minutes=10" in block
    assert "set_match_status" in RESULTS
    assert "set_match_status=_reporter_set_match_status" in APP
    assert "Startknappen blir tillgänglig 10 minuter" in RESULTS
