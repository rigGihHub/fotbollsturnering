from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
VIEW = (ROOT / "cupnavi_core" / "admin_publication_view.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()


def test_release_version():
    assert VERSION == "2026.09.04-449-MOBILE-PLAYOFF-ACTION"


def test_validation_is_lazy_outside_schema_and_control():
    assert '_validation_required_here = admin_page in {"Skapa och publicera schema", "Kontroller"}' in APP
    assert 'if sidebar_scheduled and (_validation_required_here and (_validation_dirty or not _validation_cached)):' in APP


def test_stale_validation_never_enables_publish():
    assert 'validation_ready=_validation_ready' in APP
    assert 'publish_blocked = (not quality.can_publish) or (not validation_ready)' in VIEW
    assert 'Kontrollen behöver uppdateras' in VIEW


def test_draft_skips_lifecycle_match_count_query():
    assert 'if tournament_lifecycle in ("published", "live"):' in APP
    assert 'lambda: fetch_lifecycle_match_counts(one_row, tid)' in APP
    assert '_cupnavi_admin_cache_lifecycle_counts_' in APP
