from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
WORKSPACE=(ROOT/"cupnavi_core"/"public_workspace_view.py").read_text(encoding="utf-8")
REPO=(ROOT/"cupnavi_api/repository.py").read_text(encoding="utf-8")
MAIN=(ROOT/"cupnavi_api/main.py").read_text(encoding="utf-8")

def test_streamlit_public_core_reuses_one_connection():
    block=APP[APP.index("def public_core_snapshot"):APP.index("def run_many")]
    assert block.count("with db() as con:") == 1
    assert "FROM matches m" in block
    assert "FROM teams WHERE tournament_id=?" in block
    public=WORKSPACE
    assert "_public_core = public_core_snapshot(" in public
    assert "include_matches=_needs_public_matches" in public

def test_public_api_snapshot_reuses_one_connection():
    block=REPO[REPO.index("def public_snapshot"): ]
    assert block.count("with connect() as con:") == 1
    assert "teams=many" in block and "matches=many" in block

def test_api_exposes_server_timing():
    assert '@app.middleware("http")' in MAIN
    assert 'Server-Timing' in MAIN
    assert 'X-CupNavi-Process-Ms' in MAIN
    cup=MAIN[MAIN.index('@app.get("/api/public/cups/{public_key}")'):MAIN.index('def _standings_payload')]
    assert "public_snapshot(public_key)" in cup
