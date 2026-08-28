from pathlib import Path
from cupnavi_core.observability import error_id

ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
RELEASE="2026.08.28-265-CI-E2E-HARDENING"

def test_cn_aabcb9_matches_public_page_unboundlocalerror():
    exc=UnboundLocalError("cannot access local variable 'public_page' where it is not associated with a value")
    assert error_id(exc,"render_public_view")=="CN-AABCB9"

def test_public_page_is_assigned_before_first_page_specific_read():
    start=APP.index("def render_public_view")
    end=APP.index("def render_match_reporter_view",start)
    block=APP[start:end]
    assignment=block.index("public_page = resolve_public_page(")
    assert assignment < block.index('if public_page == "Info":')
    assert assignment < block.index('if public_page == "Matcher":')

def test_release_synced():
    assert f'APP_BUILD_VERSION = "{RELEASE}"' in APP
    assert f'APP_VERSION = "{RELEASE}"' in (ROOT/"cupnavi_core/version.py").read_text(encoding="utf-8")
    assert (ROOT/"VERSION.txt").read_text().strip()==RELEASE
