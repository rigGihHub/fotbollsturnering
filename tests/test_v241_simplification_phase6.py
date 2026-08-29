from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/'app.py').read_text(encoding='utf-8')
EVENT_VIEW=(ROOT/'cupnavi_core/admin_match_events_view.py').read_text(encoding='utf-8')


def _block(start_marker,end_marker):
    start=APP.index(start_marker)
    end=APP.index(end_marker,start)
    return APP[start:end]


def test_match_events_remove_duplicate_heading_and_keep_editor_primary():
    block=_block('if admin_page == "Matchhändelser":','if admin_page == "Besöksstatistik":')
    assert 'render_admin_match_events_workspace(' in block
    assert 'st.header("Matchhändelser")' in EVENT_VIEW
    assert 'st.subheader("Registrera mål, assist, varningar och utvisningar")' not in EVENT_VIEW
    assert 'st.data_editor(' in EVENT_VIEW
    assert 'update_player_match_stats_if_unchanged(' in block
    assert 'with st.expander("Kontroll av mål & assist"' in EVENT_VIEW


def test_playoff_tree_precedes_secondary_match_list():
    block=_block('if admin_page == "Slutspel":','# --- CupNavi performance diagnostics')
    tree=block.index('render_bracket_tree(bracket["id"], public=False)')
    details=block.index('with st.expander("Matchlista", expanded=False)')
    assert tree < details
    assert 'st.caption(f"Modell: **{tournament[\'playoff_format\']}**")' in block


def test_tables_keep_tables_primary_and_hide_explanations():
    block=_block('if admin_page == "Tabeller":','if admin_page == "Skytteligor":')
    assert 'render_group_table(table, tournament, group[\'id\'])' in block
    assert 'with st.expander("Så sorteras tabellen", expanded=False)' in block
    assert 'with st.expander("Slutlig ranking", expanded=False)' in block


def test_match_event_autosave_contract_is_preserved():
    assert 'prepare_changed_event_rows(' in EVENT_VIEW
    assert 'event_validation["ok"]' in EVENT_VIEW
    assert '✓ Händelser sparas automatiskt – ingen Spara-knapp behövs.' in EVENT_VIEW
