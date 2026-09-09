from pathlib import Path


def test_runtime_and_dev_dependencies_are_separated():
    runtime = Path("requirements.txt").read_text(encoding="utf-8").lower()
    dev = Path("requirements-dev.txt").read_text(encoding="utf-8").lower()
    assert "reportlab" in runtime
    assert "pytest" not in runtime
    assert "pypdf" not in runtime
    assert "-r requirements.txt" in dev
    assert "pytest" in dev
    assert "pypdf" in dev


def test_ci_installs_dev_requirements_and_runs_pytest():
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "pip install -r requirements-dev.txt" in workflow
    assert "pip check" in workflow
    assert "run: pytest" in workflow
