from pathlib import Path
from datetime import datetime
import importlib.util
import sys

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")


def _load():
    spec = importlib.util.spec_from_file_location("cup_day_dashboard_v362", ROOT / "cupnavi_core" / "cup_day_dashboard.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_primary_guidance_prioritizes_overdue_results_before_other_work():
    mod = _load()
    now = datetime(2026, 9, 1, 10, 0)
    snapshot = {
        "reporting_due": [{"scheduled_start": "2026-09-01T08:00:00"}],
        "live": [{"scheduled_start": "2026-09-01T09:50:00"}],
        "next_window": [{"scheduled_start": "2026-09-01T10:20:00"}],
        "upcoming": [],
        "today_total": 3,
    }
    result = mod.cup_day_primary_guidance(snapshot, now=now)
    assert result["state"] == "action"
    assert "Rapportera" in result["title"]
    assert result["target"] == "Matcher och resultat"


def test_primary_guidance_uses_next_match_when_nothing_is_urgent():
    mod = _load()
    now = datetime(2026, 9, 1, 10, 0)
    match = {"scheduled_start": "2026-09-01T10:25:00"}
    result = mod.cup_day_primary_guidance(
        {"reporting_due": [], "live": [], "next_window": [match], "upcoming": [match], "today_total": 1},
        now=now,
    )
    assert result["state"] == "next"
    assert "25 min" in result["title"]


def test_cup_day_screen_has_one_primary_message_then_progressive_disclosure():
    section = APP[APP.index('if admin_page == "Cupdagen":'):APP.index('if admin_page == "Cupverktyg":')]
    assert 'cup_day_primary_guidance' in section
    assert 'type="primary"' in section
    assert 'st.markdown("### Härnäst")' in section
    assert 'with st.expander("Planstatus", expanded=False)' in section
    assert 'with st.expander("Fler åtgärder", expanded=False)' in section
    assert 'Senare idag · {len(_later_matches)} matcher' in section


def test_live_and_upcoming_cards_are_mobile_first_without_side_column_buttons():
    section = APP[APP.index('if admin_page == "Cupdagen":'):APP.index('if admin_page == "Cupverktyg":')]
    assert '_lc1, _lc2 = st.columns' not in section
    assert '_nc1, _nc2 = st.columns' not in section
    assert '"Öppna matchen"' in section


def test_version():
    assert 'APP_BUILD_VERSION = "2026.09.02-390-PUBLIC-SHARE-TOPLIST-UX"' in APP
