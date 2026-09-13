from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADMIN_CSS = (ROOT / "frontend-next/src/app/v618-admin.css").read_text(encoding="utf-8")


def test_mobile_admin_rows_stack_without_horizontal_overflow():
    assert "@media(max-width:900px)" in ADMIN_CSS
    assert ".admin-team-list article{grid-template-columns:minmax(0,1fr)" in ADMIN_CSS
    assert ".admin-team-list article label{min-width:0!important" in ADMIN_CSS


def test_mobile_admin_controls_stay_inside_cards():
    assert ".admin-panel input,.admin-panel select,.admin-panel textarea" in ADMIN_CSS
    assert "width:100%;max-width:100%;min-width:0" in ADMIN_CSS
    assert ".admin-lock{max-width:100%;white-space:normal" in ADMIN_CSS


def test_mobile_admin_status_rows_wrap_readably():
    assert ".admin-code-placeholder{align-items:flex-start;flex-direction:column" in ADMIN_CSS
    assert ".admin-checks>div{grid-template-columns:24px minmax(0,1fr)}" in ADMIN_CSS
    assert ".admin-checks small{grid-column:2}" in ADMIN_CSS
