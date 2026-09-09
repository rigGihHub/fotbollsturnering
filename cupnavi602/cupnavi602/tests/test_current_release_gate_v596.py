from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
VERSION = ROOT / "cupnavi_core" / "version.py"


def test_v596_version_is_synchronized():
    assert 'APP_BUILD_VERSION = "2026.09.09-596-IMPORT-HOTFIX"' in APP
    assert 'APP_VERSION = "2026.09.09-596-IMPORT-HOTFIX"' in VERSION.read_text(encoding="utf-8")


def test_v596_release_ui_label_is_importable():
    spec = importlib.util.spec_from_file_location("cupnavi_version_smoke", VERSION)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    assert module.release_ui_label(module.APP_VERSION) == "CupNavi 2026.09.09-596-IMPORT-HOTFIX"


def test_app_import_contract_names_exist():
    assert "from cupnavi_core.version import APP_VERSION as IMPORTED_CORE_APP_VERSION, release_ui_label" in APP
