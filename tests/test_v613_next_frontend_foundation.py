from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = "2026.09.10-615-NEXT-VISUAL-RUNTIME-HARDENING"

def test_version_sync():
    assert EXPECTED in (ROOT / "VERSION.txt").read_text()
    assert EXPECTED in (ROOT / "cupnavi_core/version.py").read_text()
    assert EXPECTED in (ROOT / "app.py").read_text()

def test_next_app_exists():
    assert (ROOT / "frontend-next/package.json").exists()
    assert (ROOT / "frontend-next/src/app/cup/[publicKey]/page.tsx").exists()

def test_public_api_is_used():
    api = (ROOT / "frontend-next/src/lib/api.ts").read_text()
    assert "/api/public/cups/" in api
    assert 'cache: "no-store"' in api

def test_signature_design_layers_exist():
    css = (ROOT / "frontend-next/src/app/globals.css").read_text()
    for token in ["--paper:#f4f1e8", ".match-card", ".score-window", ".texttv", ".collectible-stamp"]:
        assert token in css

def test_streamlit_is_parallel_not_removed():
    assert (ROOT / "app.py").exists()
    assert (ROOT / "frontend-next/README.md").exists()
