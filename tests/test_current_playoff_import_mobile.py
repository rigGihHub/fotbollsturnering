from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI = (ROOT / "frontend-next" / "src" / "components" / "playoff-import-review.tsx").read_text(encoding="utf-8")


def test_playoff_import_dialog_fits_mobile_viewport():
    assert 'width:"min(1040px,calc(100vw - 20px))"' in UI
    assert 'overflowX:"hidden"' in UI


def test_playoff_import_fields_wrap_instead_of_forcing_desktop_columns():
    assert 'repeat(auto-fit,minmax(150px,1fr))' in UI
    assert 'minWidth:0' in UI


def test_long_playoff_rule_payload_cannot_force_horizontal_scroll():
    assert 'overflowWrap:"anywhere"' in UI
