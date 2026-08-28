
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")


def _block(start_marker,end_marker):
    start=APP.index(start_marker)
    end=APP.index(end_marker,start)
    return APP[start:end]


def test_results_page_prioritizes_result_editor():
    block=_block('if admin_page == "Matcher och resultat":','if admin_page == "Matchhändelser":')
    assert 'st.header("Resultat")' in block
    assert 'st.caption("Registrera resultat match för match eller använd massinmatning när det passar.")' in block
    assert 'st.data_editor(' in block
    assert 'with st.expander("Visa hela matchschemat", expanded=False)' in block
    assert block.index('st.caption("Registrera resultat match för match eller använd massinmatning när det passar.")') < block.index('with st.expander("Visa hela matchschemat", expanded=False)')


def test_results_page_keeps_auto_save_and_concurrency_guards():
    block=_block('if admin_page == "Matcher och resultat":','if admin_page == "Matchhändelser":')
    assert "update_match_result_if_unchanged(" in block
    assert 'st.caption("✓ Ändringar sparas automatiskt – ingen Spara-knapp behövs.")' in block
    assert "bulk_result_conflict_message" in block


def test_playoff_help_is_progressively_disclosed():
    block=_block('if admin_page == "Matcher och resultat":','if admin_page == "Matchhändelser":')
    assert 'with st.expander("Regler vid oavgjort i slutspel", expanded=False)' in block
    assert 'with st.expander(f"Kommande slutspelsmatcher · {unresolved_count} väntar på lag", expanded=False)' in block


def test_referee_creation_keeps_name_primary_and_contact_optional():
    block=_block('if admin_page == "Domare":','if admin_page == "Skapa och publicera schema":')
    assert 'rname = st.text_input("Namn")' in block
    assert 'with st.expander("Kontaktuppgifter", expanded=False)' in block
    assert 'st.form_submit_button("Lägg till domare", type="primary", use_container_width=True)' in block


def test_referee_list_is_collapsed_but_available():
    block=_block('if admin_page == "Domare":','if admin_page == "Skapa och publicera schema":')
    assert 'with st.expander("Visa domarlista & kontaktuppgifter", expanded=False)' in block
    assert 'render_centered_table(pd.DataFrame([' in block
