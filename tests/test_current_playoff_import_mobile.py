from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI = (ROOT / "frontend-next" / "src" / "components" / "playoff-import-review.tsx").read_text(encoding="utf-8")
CSS = (ROOT / "frontend-next/src/components/playoff-import-review.module.css").read_text(encoding="utf-8")


def test_playoff_import_dialog_fits_mobile_viewport():
    assert 'height:100dvh' in CSS
    assert 'overflow-x:hidden' in CSS
    assert 'min-height:0' in CSS


def test_playoff_import_fields_wrap_instead_of_forcing_desktop_columns():
    assert 'repeat(2,minmax(0,1fr))' in CSS
    assert 'grid-column:1 / -1' in CSS
    assert 'min-width:0' in CSS


def test_long_playoff_rule_payload_cannot_force_horizontal_scroll():
    assert 'overflow-wrap:anywhere' in CSS
    assert 'JSON.stringify(review.playoff_rule_values' not in UI
    assert 'playoffImportRules' in UI


def test_error_and_actions_share_visible_footer_outside_scroll_body():
    footer = UI.split('<div className={styles.footer}>',1)[1]
    assert 'role="alert"' in footer
    assert 'styles.actions' in footer
    assert '.footer { flex-shrink:0' in CSS
    assert 'window.confirm' not in UI
