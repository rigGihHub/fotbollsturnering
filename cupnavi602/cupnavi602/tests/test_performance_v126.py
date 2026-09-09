import re
from pathlib import Path


def test_competition_class_sync_is_not_run_globally_on_every_rerun():
    text = Path("app.py").read_text(encoding="utf-8")
    marker = 'tournament = next(t for t in tournaments if t["id"] == tid)'
    start = text.index(marker)
    block = text[start:start+700]
    assert "sync_competition_classes(tid)" not in block
    assert "Do not perform remote" in block


def test_release_version_is_synced():
    text = Path("app.py").read_text(encoding="utf-8")
    version = Path("VERSION.txt").read_text(encoding="utf-8").strip()
    core = Path("cupnavi_core/version.py").read_text(encoding="utf-8")
    assert re.match(r"^20\d{2}\.\d{2}\.\d{2}-", version)
    assert version in text
    assert version in core
