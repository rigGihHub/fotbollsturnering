from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()


def test_release_version():
    assert VERSION == "2026.09.04-449-MOBILE-PLAYOFF-ACTION"
    assert 'APP_BUILD_VERSION = "2026.09.04-449-MOBILE-PLAYOFF-ACTION"' in APP


def test_short_session_ttl_fast_path_exists():
    assert "def _session_ttl_get(key, ttl_seconds, factory):" in APP
    assert "_cupnavi_public_core_v434_" in APP
    assert "_cupnavi_public_info_boot_v434_" in APP
    assert "_cupnavi_public_events_v434_" in APP
    assert "_cupnavi_public_tournament_v434_" in APP


def test_live_data_ttls_stay_short():
    assert "_session_ttl_get(session_key, 6.0, _load_public_core)" in APP
    assert "8.0, _load_info_boot" in APP
    assert "5.0, _load_events" in APP
    assert "12.0," in APP
