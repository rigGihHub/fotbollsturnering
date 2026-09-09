from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "app.py"
SRC = APP.read_text(encoding="utf-8")


def test_admin_shell_uses_short_ttl_tournament_snapshot():
    assert "def admin_tournament_list_snapshot" in SRC
    assert SRC.count("admin_tournament_list_snapshot()") >= 2
    assert '"_cupnavi_shell_cache_admin_tournaments"' in SRC


def test_public_discovery_uses_short_ttl_tournament_snapshot():
    assert "def public_tournament_list_snapshot" in SRC
    assert "tournaments = public_tournament_list_snapshot()" in SRC


def test_shell_and_direct_public_caches_are_invalidated_after_writes():
    signature = 'def _clear_session_read_caches(prefixes=("_cupnavi_admin_cache_", "_cupnavi_shell_cache_", "_cupnavi_public_tournament_v434_")):'
    assert signature in SRC
    assert "_clear_session_read_caches()" in SRC
