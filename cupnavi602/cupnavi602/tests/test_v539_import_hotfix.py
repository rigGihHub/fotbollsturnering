from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parents[1]
RELEASE = "2026.09.08-539-IMPORT-HOTFIX"

def _load_version_module():
    path = ROOT / "cupnavi_core" / "version.py"
    spec = importlib.util.spec_from_file_location("cupnavi_version_v539", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module

def test_release_ui_label_is_importable_and_correct():
    module = _load_version_module()
    assert module.APP_VERSION == RELEASE
    assert module.release_ui_label(RELEASE) == "Version v1.539"

def test_app_and_version_file_are_synced():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    assert f'APP_BUILD_VERSION = "{RELEASE}"' in app
    assert (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip() == RELEASE
    assert "release_ui_label" in app
