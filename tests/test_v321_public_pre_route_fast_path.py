from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()


def test_v321_version():
    assert VERSION == "2026.09.03-414-PITCH-TIMING-MODE"


def test_public_view_has_css_fast_path_branch():
    anchor = '# v321: public reruns do not need the large BaseWeb datepicker/admin CSS payload.'
    assert anchor in APP
    block = APP[APP.index(anchor): APP.index('def render_initial_tournament_setup', APP.index(anchor))]
    assert 'if view_mode == "Turneringsvy":' in block
    assert '/* PUBLIC VIEW POLISH V192 */' in block
    assert '/* CUPNAVI CALENDAR FINAL OVERRIDE */' in block


def test_calendar_css_is_only_in_non_public_branch():
    anchor = '# v321: public reruns do not need the large BaseWeb datepicker/admin CSS payload.'
    block = APP[APP.index(anchor): APP.index('def render_initial_tournament_setup', APP.index(anchor))]
    public_branch, non_public_branch = block.split('else:', 1)
    assert '/* PUBLIC VIEW POLISH V192 */' in public_branch
    assert '/* CUPNAVI CALENDAR FINAL OVERRIDE */' not in public_branch
    assert '/* CUPNAVI CALENDAR FINAL OVERRIDE */' in non_public_branch


def test_shared_readability_kept_for_both_branches():
    anchor = '# v321: public reruns do not need the large BaseWeb datepicker/admin CSS payload.'
    block = APP[APP.index(anchor): APP.index('def render_initial_tournament_setup', APP.index(anchor))]
    public_branch, non_public_branch = block.split('else:', 1)
    assert 'GLOBAL READABILITY PASS' in public_branch
    assert 'GLOBAL READABILITY PASS' in non_public_branch
