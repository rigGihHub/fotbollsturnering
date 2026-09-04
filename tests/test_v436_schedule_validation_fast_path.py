from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
VIEW=(ROOT/'cupnavi_core'/'schedule_workspace_view.py').read_text(encoding='utf-8')
APP=(ROOT/'app.py').read_text(encoding='utf-8')
VERSION=(ROOT/'VERSION.txt').read_text(encoding='utf-8').strip()

def test_v436_version():
    assert VERSION == '2026.09.04-449-MOBILE-PLAYOFF-ACTION'

def test_schema_reuses_shell_snapshots():
    assert 'rules_snapshot: Any | None = None' in VIEW
    assert 'validation_snapshot: tuple[list[Any], list[Any], list[Any]] | None = None' in VIEW
    assert 'rules_snapshot=sidebar_rules' in APP
    assert 'validation_snapshot=(sidebar_errors, sidebar_warnings, _sidebar_quality)' in APP
    assert 'if validation_snapshot is not None:' in VIEW

def test_group_details_are_truly_lazy():
    assert '"Visa detaljer per grupp"' in VIEW
    assert 'if _show_group_details:' in VIEW
    assert 'with st.expander("Detaljer per grupp", expanded=False):' not in VIEW
