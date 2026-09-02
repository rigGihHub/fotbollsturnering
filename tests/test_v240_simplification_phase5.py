
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
RESULTS_VIEW=(ROOT/"cupnavi_core"/"admin_results_view.py").read_text(encoding="utf-8")


def _block(start_marker,end_marker):
    start=APP.index(start_marker)
    end=APP.index(end_marker,start)
    return APP[start:end]


def test_results_page_prioritizes_result_editor():
    block=RESULTS_VIEW
    assert '<div class="title">Resultat</div>' in block
    assert '"Att rapportera", "Alla matcher"' in block
    assert 'st.data_editor(' in block
    assert 'show_full_result_schedule = st.toggle(' in block
    assert '"Visa hela matchschemat"' in block
    assert block.index('"Att rapportera", "Alla matcher"') > block.index('show_full_result_schedule = st.toggle(')


def test_results_page_keeps_auto_save_and_concurrency_guards():
    app_block=_block('if admin_page == "Matcher och resultat":','if admin_page == "Matchhändelser":')
    assert "update_match_result_if_unchanged(" in app_block
    assert 'st.caption("✓ Ändringar sparas automatiskt – ingen Spara-knapp behövs.")' in RESULTS_VIEW
    assert "bulk_result_conflict_message" in RESULTS_VIEW
    assert 'save_result_updates=_save_admin_result_updates' in app_block


def test_playoff_help_is_progressively_disclosed():
    block=RESULTS_VIEW
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
