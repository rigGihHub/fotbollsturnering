from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
app=(ROOT/"app.py").read_text(encoding="utf-8")
public_workspace=(ROOT/"cupnavi_core/public_workspace_view.py").read_text(encoding="utf-8")
repo=(ROOT/"cupnavi_api/repository.py").read_text(encoding="utf-8")
main=(ROOT/"cupnavi_api/main.py").read_text(encoding="utf-8")
assert "def public_core_snapshot" in app
assert "_public_core = public_core_snapshot(" in public_workspace
assert "include_matches=_needs_public_matches" in public_workspace
assert "def public_snapshot" in repo and "with connect() as con:" in repo[repo.index("def public_snapshot"):]
assert "Server-Timing" in main and "X-CupNavi-Process-Ms" in main
print("Performance contract OK")
