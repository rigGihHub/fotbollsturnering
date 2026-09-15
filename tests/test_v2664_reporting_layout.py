from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_reporting_layout_is_scoped_and_loaded_last():
    css = (ROOT / "frontend-next/src/app/reporting-admin-v2664.css").read_text()
    layout = (ROOT / "frontend-next/src/app/layout.tsx").read_text()
    assert 'html[data-admin-step="reporting"] #team-codes' in css
    assert 'html[data-admin-step="reporting"] #referee-codes' in css
    assert 'grid-template-columns: minmax(220px, 1fr) auto !important' in css
    assert 'word-break: normal !important' in css
    assert 'import "./reporting-admin-v2664.css"' in layout
    assert layout.index('public-masterpiece-v2658.css') < layout.index('reporting-admin-v2664.css')


def test_reporting_actions_have_a_mobile_layout():
    css = (ROOT / "frontend-next/src/app/reporting-admin-v2664.css").read_text()
    assert '@media (max-width: 760px)' in css
    assert '@media (max-width: 430px)' in css
    assert 'grid-template-columns: minmax(0, 1fr) !important' in css
