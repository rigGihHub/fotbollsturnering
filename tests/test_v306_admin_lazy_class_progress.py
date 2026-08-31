from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()


def _overview_block():
    start = APP.index('elif admin_page == "Adminöversikt":')
    end = APP.index('if admin_page == "Cupinställningar":', start)
    return APP[start:end]


def test_release_version():
    assert VERSION == "2026.08.31-354-ADDRESS-READINESS-FIX"


def test_class_progress_query_removed_from_default_overview():
    block = _overview_block()
    advanced = block.index('if show_overview_advanced:')
    assert '"Visa lagfördelning per klass"' not in block[:advanced]
    assert 'GROUP BY competition_class_id' not in block[:advanced]


def test_class_progress_detail_remains_available_in_core_helper():
    core = (ROOT / "cupnavi_core" / "admin_overview.py").read_text(encoding="utf-8")
    assert 'def class_progress_caption(' in core
    assert 'Lag per tävlingsklass' in core
