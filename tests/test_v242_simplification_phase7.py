
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/'app.py').read_text(encoding='utf-8')


def _block(start_marker,end_marker):
    start=APP.index(start_marker)
    end=APP.index(end_marker,start)
    return APP[start:end]


def test_sponsors_keep_primary_name_and_hide_optional_fields():
    block=_block('if admin_page == "Sponsorer":','if admin_page == "Funktionärer":')
    assert 'sponsor_name = st.text_input("Namn *"' in block
    assert 'with st.expander("Fler sponsoruppgifter", expanded=False)' in block
    assert 'st.form_submit_button("Lägg till sponsor", type="primary"' in block


def test_offers_keep_primary_fields_and_hide_optional_fields():
    block=_block('if admin_page == "Erbjudanden":','if admin_page == "Import":')
    assert 'offer_title = st.text_input("Rubrik *"' in block
    assert 'offer_business = st.text_input("Företag / restaurang"' in block
    assert 'with st.expander("Fler erbjudandeuppgifter", expanded=False)' in block


def test_functionaries_prioritize_name_and_role():
    block=_block('if admin_page == "Funktionärer":','if admin_page == "Import":')
    assert 'fn_name = fc1.text_input("Namn *")' in block
    assert 'fn_role = fc2.selectbox(' in block
    assert 'with st.expander("Fler funktionärsuppgifter", expanded=False)' in block
    assert 'with st.expander("Visa funktionärslista", expanded=False)' in block
    assert 'with st.expander("Funktionärsschema & arbetspass", expanded=False)' in block


def test_import_auto_mapping_is_progressively_disclosed():
    block=_block('if admin_page == "Import":','if admin_page == "Cupverktyg":')
    assert 'st.header("Import")' in block
    assert 'required_auto_missing = any(' in block
    assert 'with st.expander("Kolumnmappning", expanded=required_auto_missing)' in block
    assert 'with st.expander("Visa importdetaljer", expanded=bool(error_count))' in block
    assert 'st.subheader("Importera")' in block


def test_import_atomic_write_safeguards_remain():
    block=_block('if admin_page == "Import":','if admin_page == "Cupverktyg":')
    assert 'con.execute("BEGIN IMMEDIATE")' in block
    assert 'con.rollback()' in block
    assert 'TeamLimitReachedError' in block
