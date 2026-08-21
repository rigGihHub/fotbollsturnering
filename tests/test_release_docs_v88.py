from pathlib import Path

def test_release_contains_only_current_quality_doc():
    quality = sorted(path.name for path in Path(".").glob("QUALITY_V*.md"))
    assert quality == ["QUALITY_V88.md"]

def test_release_contains_no_ux_history_docs():
    assert list(Path(".").glob("UX_V*.md")) == []
