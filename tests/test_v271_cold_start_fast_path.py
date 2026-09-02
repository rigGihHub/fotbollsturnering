from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()
CORE_VERSION = (ROOT / "cupnavi_core" / "version.py").read_text(encoding="utf-8")
SCHEDULE = (ROOT / "cupnavi_core" / "schedule_workspace_view.py").read_text(encoding="utf-8")


def test_v271_version_is_synchronized():
    assert VERSION == "2026.09.02-390-PUBLIC-SHARE-TOPLIST-UX"
    assert f'APP_BUILD_VERSION = "{VERSION}"' in APP
    assert f'APP_VERSION = "{VERSION}"' in CORE_VERSION


def test_source_fingerprint_uses_metadata_not_source_file_contents():
    start = APP.index("def _compute_source_fingerprint")
    end = APP.index("def _refresh_cupnavi_imports_if_sources_changed")
    block = APP[start:end]
    assert ".stat()" in block
    assert "rglob(" not in block
    assert "stat.st_size" in block
    assert "stat.st_mtime_ns" in block
    assert 'root / "VERSION.txt"' in block
    assert "data = path.read_bytes()" not in block


def test_secondary_heavy_features_are_not_global_imports():
    header = APP[: APP.index("APP_BUILD_VERSION")]
    assert "from cupnavi_core.pdf_export import build_schedule_pdf" not in header
    assert "from cupnavi_core.ai_roster_import" not in header
    assert "from cupnavi_core.import_service import" not in header
    assert "import qrcode" not in header


def test_secondary_features_still_have_lazy_imports_at_use_sites():
    assert "from cupnavi_core.pdf_export import build_schedule_pdf" in SCHEDULE
    assert "from cupnavi_core.ai_roster_import import extract_roster_from_image" in APP
    assert "from cupnavi_core.import_service import (" in APP
    assert "import qrcode" in APP
