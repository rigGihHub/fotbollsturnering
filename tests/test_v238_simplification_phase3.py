
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")


def _block(start_marker,end_marker):
    start=APP.index(start_marker)
    end=APP.index(end_marker,start)
    return APP[start:end]


def test_team_page_hides_secondary_operations():
    block=_block('if admin_page == "Lag":','if admin_page == "Grupper":')
    for label in [
        'with st.expander("Fler laguppgifter", expanded=False)',
        'with st.expander("Digital lagincheckning", expanded=False)',
        'with st.expander("Lagportal – koder", expanded=False)',
        'with st.expander("Lagmeddelanden", expanded=False)',
        'with st.expander("Redigera eller ta bort lag", expanded=False)',
    ]:
        assert label in block
    assert 'if st.button("Lägg till lag", type="primary"' in block


def test_groups_page_removes_duplicate_heading_and_keeps_main_flow():
    block=_block('if admin_page == "Grupper":','if admin_page == "Trupper":')
    assert block.count('st.header("Grupper")') == 1
    assert 'st.subheader("Grupper")' not in block
    assert 'st.subheader("Placera lagen i rätt grupp")' in block
    assert 'with st.expander("Redigera eller ta bort grupp")' in block


def test_roster_page_keeps_player_creation_primary():
    block=_block('if admin_page == "Trupper":','if admin_page == "Domare":')
    assert 'st.form("new_player"' in block
    assert 'st.form_submit_button("Lägg till spelare", type="primary")' in block
    assert 'with st.expander("Matchtrupper – admin", expanded=False)' in block
    assert '["Ej angiven", "Målvakt", "Försvarare", "Mittfältare", "Anfallare"]' in block


def test_portal_rules_remain_available():
    block=_block('if admin_page == "Trupper":','if admin_page == "Domare":')
    assert 'with st.expander("⚙️ Regler för Lagportal och matchtrupper", expanded=False)' in block
    assert 'UPDATE tournaments SET max_roster_size=?' in block
