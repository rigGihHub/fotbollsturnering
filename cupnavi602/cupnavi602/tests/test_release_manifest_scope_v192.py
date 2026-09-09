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
    assert module.is_release_file(module.ROOT / "scripts" / "check_health_contract.py", Path("scripts/check_health_contract.py"))
    assert module.is_release_file(module.ROOT / "staging" / "Caddyfile", Path("staging/Caddyfile"))
    assert not module.is_release_file(module.ROOT / "QUALITY_V190.md", Path("QUALITY_V190.md"))
    assert not module.is_release_file(module.ROOT / "turnering.db", Path("turnering.db"))


def test_nested_repo_copies_under_legitimate_dirs_are_ignored():
    module = _load_manifest_module()
    bad = [
        "cupnavi_core/app.py",
        "cupnavi_core/.github/workflows/ci.yml",
        "cupnavi_core/cupnavi_core/version.py",
        "scripts/app.py",
        "scripts/.github/workflows/ci.yml",
        "scripts/tests/test_fake.py",
        "scripts/scripts/check_fake.py",
        "staging/app.py",
        "staging/.github/workflows/ci.yml",
        "staging/tests/test_fake.py",
        "staging/staging/Caddyfile",
    ]
    for raw in bad:
        rel = Path(raw)
        assert not module.is_release_file(module.ROOT / rel, rel), raw


def test_release_files_never_recurse_into_scripts_staging_or_core(tmp_path):
    module = _load_manifest_module()
    baseline = module.render()
    created = [
        module.ROOT / "scripts" / "tests" / "test_old_copy.py",
        module.ROOT / "scripts" / "app.py",
        module.ROOT / "staging" / "cupnavi_core" / "version.py",
        module.ROOT / "staging" / "VERSION.txt",
        module.ROOT / "cupnavi_core" / "tests" / "test_old_copy.py",
    ]
    try:
        for path in created:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("legacy", encoding="utf-8")
        assert module.render() == baseline
    finally:
        for path in reversed(created):
            path.unlink(missing_ok=True)
        for d in [
            module.ROOT / "scripts" / "tests",
            module.ROOT / "staging" / "cupnavi_core",
            module.ROOT / "cupnavi_core" / "tests",
        ]:
            try:
                d.rmdir()
            except OSError:
                pass


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
