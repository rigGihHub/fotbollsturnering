from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
VERSION = "2026.08.31-347-SCHEDULE-READINESS-POLISH"


def test_release_version_is_v338():
    assert (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip() == VERSION
    assert f'APP_BUILD_VERSION = "{VERSION}"' in APP
    assert VERSION in (ROOT / "cupnavi_core" / "version.py").read_text(encoding="utf-8")


def test_global_participant_navigation_only_exposes_teams_and_groups():
    nav = APP[APP.index("ADMIN_NAV_GROUPS = ["):APP.index("ADMIN_NAV = [")]
    participant_line = next(line for line in nav.splitlines() if '("Deltagare",' in line)
    assert '("Lag", tr("Lag"))' in participant_line
    assert '("Grupper", tr("Grupper"))' in participant_line
    assert '"Trupper"' not in participant_line
    assert '"Önskemålscentral"' not in participant_line
    assert '"Import"' not in participant_line


def test_secondary_participant_tools_remain_available_from_teams():
    assert 'with st.expander("Fler lagverktyg", expanded=False):' in APP
    assert 'args=("Trupper",)' in APP
    assert 'args=("Önskemålscentral",)' in APP
    assert 'args=("Import",)' in APP


def test_hidden_participant_tools_stay_in_participant_group():
    assert 'if page in {"Trupper", "Önskemålscentral", "Import"}:' in APP
    assert 'return "Deltagare"' in APP


def test_existing_participant_write_paths_remain():
    assert 'if admin_page == "Trupper":' in APP
    assert 'if admin_page == "Önskemålscentral":' in APP
    assert 'if admin_page == "Import":' in APP
    assert 'save_event_rows' in APP
