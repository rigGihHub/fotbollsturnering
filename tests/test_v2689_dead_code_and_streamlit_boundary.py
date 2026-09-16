from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPONENTS = ROOT / "frontend-next" / "src" / "components"


def test_release_version_is_synchronized():
    assert '"version": "2.6.95"' in (ROOT / "frontend-next/package.json").read_text(encoding="utf-8")
    assert '"version": "2.6.95"' in (ROOT / "frontend-next/package-lock.json").read_text(encoding="utf-8")
    assert 'const APP_VERSION = "2.6.95";' in (ROOT / "frontend-next/src/app/layout.tsx").read_text(encoding="utf-8")
    assert 'const CACHE="cupnavi-next-v2695";' in (ROOT / "frontend-next/public/sw.js").read_text(encoding="utf-8")


def test_superseded_next_components_are_removed():
    removed = {
        "CupShareButton.tsx",
        "admin-runtime-ux.tsx",
        "admin-session-cache-guard.tsx",
        "admin-workspace-resilient.tsx",
        "cup-create-launcher-v2.tsx",
        "cup-create-launcher-v3.tsx",
        "cup-create-launcher-v4.tsx",
        "cup-create-launcher-v5.tsx",
        "cup-create-launcher.tsx",
        "cup-setup-guide.tsx",
        "import-recovery-guard.tsx",
    }
    assert not [name for name in removed if (COMPONENTS / name).exists()]


def test_streamlit_is_not_part_of_the_production_api_container():
    dockerfile = (ROOT / "Dockerfile.api").read_text(encoding="utf-8")
    requirements = (ROOT / "requirements-api.txt").read_text(encoding="utf-8")
    assert "COPY app.py" not in dockerfile
    assert "uvicorn" in dockerfile
    assert "requirements-api.txt" in dockerfile
    dependency_lines = [line.casefold() for line in requirements.splitlines() if line and not line.startswith("#")]
    assert not any(line.startswith("streamlit") for line in dependency_lines)
    assert not any(line.startswith("pandas") for line in dependency_lines)


def test_streamlit_remains_quarantined_until_parity_gaps_are_closed():
    audit = (ROOT / "STREAMLIT_TO_NEXT_PARITY_AUDIT.md").read_text(encoding="utf-8")
    assert "all Streamlit functionality has not yet been transferred" in audit
    assert "P0 – match reporting parity" in audit
