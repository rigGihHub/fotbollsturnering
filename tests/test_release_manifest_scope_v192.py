from pathlib import Path
import importlib.util


def _load_manifest_module():
    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "generate_release_manifest.py"
    spec = importlib.util.spec_from_file_location("release_manifest", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_release_manifest_uses_explicit_release_scope():
    module = _load_manifest_module()
    assert module.is_release_file(module.ROOT / "app.py", Path("app.py"))
    assert module.is_release_file(module.ROOT / "cupnavi_core" / "version.py", Path("cupnavi_core/version.py"))
    assert module.is_release_file(module.ROOT / ".github" / "workflows" / "ci.yml", Path(".github/workflows/ci.yml"))
    assert not module.is_release_file(module.ROOT / "QUALITY_V190.md", Path("QUALITY_V190.md"))
    assert not module.is_release_file(module.ROOT / "old_notes.md", Path("old_notes.md"))
    assert not module.is_release_file(module.ROOT / "turnering.db", Path("turnering.db"))


def test_unrelated_top_level_file_does_not_change_render(tmp_path, monkeypatch):
    module = _load_manifest_module()
    baseline = module.render()
    extra = module.ROOT / "OLD_RELEASE_NOTE_V001.md"
    try:
        extra.write_text("historical note", encoding="utf-8")
        assert module.render() == baseline
    finally:
        extra.unlink(missing_ok=True)


def test_manifest_diagnostics_identifies_changed_missing_and_extra_files():
    module = _load_manifest_module()
    a = "\n".join([
        "# CupNavi release manifest",
        "# version: demo",
        "# sha256  path",
        f"{'1'*64}  ./app.py",
        f"{'2'*64}  ./obsolete.txt",
        "",
    ])
    e = "\n".join([
        "# CupNavi release manifest",
        "# version: demo",
        "# sha256  path",
        f"{'3'*64}  ./app.py",
        f"{'4'*64}  ./new.txt",
        "",
    ])
    detail = module.manifest_diagnostics(a, e)
    assert "CHANGED: app.py" in detail
    assert "MISSING_FROM_MANIFEST: new.txt" in detail
    assert "EXTRA_IN_MANIFEST: obsolete.txt" in detail
    assert "manifest_sha256=" in detail
    assert "current_sha256=" in detail


def test_nested_legacy_project_inside_core_is_ignored():
    module = _load_manifest_module()
    assert not module.is_release_file(
        module.ROOT / "cupnavi_core" / "app.py",
        Path("cupnavi_core/app.py"),
    )
    assert not module.is_release_file(
        module.ROOT / "cupnavi_core" / ".github" / "workflows" / "ci.yml",
        Path("cupnavi_core/.github/workflows/ci.yml"),
    )
    assert not module.is_release_file(
        module.ROOT / "cupnavi_core" / "cupnavi_core" / "version.py",
        Path("cupnavi_core/cupnavi_core/version.py"),
    )
    assert module.is_release_file(
        module.ROOT / "cupnavi_core" / "version.py",
        Path("cupnavi_core/version.py"),
    )
