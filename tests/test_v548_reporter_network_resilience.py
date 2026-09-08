from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTER = (ROOT / "cupnavi_core" / "match_reporter_workspace_view.py").read_text(encoding="utf-8")
APP = (ROOT / "app.py").read_text(encoding="utf-8")

def test_v548_version():
    version = (ROOT / "VERSION.txt").read_text().strip()
    assert version == "2026.09.08-548-REPORTER-NETWORK-RESILIENCE"
    assert version in APP

def test_reporter_has_explicit_save_states():
    assert '"saving"' in REPORTER
    assert '"saved"' in REPORTER
    assert '"uncertain"' in REPORTER
    assert "Sparar…" in REPORTER
    assert "Sparstatus osäker" in REPORTER

def test_reporter_has_live_browser_network_probe():
    assert "navigator.onLine" in REPORTER
    assert "Dåligt nät / offline" in REPORTER
    assert "window.addEventListener('online',draw)" in REPORTER
    assert "window.addEventListener('offline',draw)" in REPORTER

def test_uncertain_write_requires_server_refresh_not_automatic_retry():
    assert "Läs om från servern" in REPORTER
    assert "ingen automatisk omskrivning" in REPORTER
    assert "innan du försöker igen" in REPORTER

def test_existing_safety_contracts_are_retained():
    assert "REPORTER_CORRECTION_WINDOW_SECONDS = 15" in REPORTER
    assert "REPORTER_NOTIFICATION_DEBOUNCE_SECONDS = 30" in REPORTER
    assert "deps.save_live_goal(" in REPORTER
    assert "deps.undo_live_goal(" in REPORTER
