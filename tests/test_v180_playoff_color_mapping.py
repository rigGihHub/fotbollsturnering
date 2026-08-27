from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
R="2026.08.27-208-PUBLIC-MATCH-PERFORMANCE-REVIEW"

def test_placement_playoffs_have_distinct_classes():
    for token in ("qual-rank-1","qual-rank-2","qual-rank-3","qual-rank-4"):
        assert token in APP

def test_placement_names_are_detected():
    for token in ("ettornas","tvåornas","treornas","fyrornas"):
        assert token in APP

def test_a_b_mapping_still_exists():
    assert 'mapping[rank] = ("A", "qual-a")' in APP
    assert 'mapping[rank] = ("B", "qual-b")' in APP

def test_distinct_row_colors_exist():
    assert ".texttv-table tr.qual-rank-1 td" in APP
    assert ".texttv-table tr.qual-rank-2 td" in APP
    assert ".texttv-table tr.qual-rank-3 td" in APP
    assert ".texttv-table tr.qual-rank-4 td" in APP

def test_release_sync():
    assert f'APP_BUILD_VERSION = "{R}"' in APP
    assert f'APP_VERSION = "{R}"' in (ROOT/"cupnavi_core/version.py").read_text(encoding="utf-8")
    assert (ROOT/"VERSION.txt").read_text().strip()==R
