from pathlib import Path

APP = Path('app.py').read_text()
SETUP = Path('cupnavi_core/initial_setup_view.py').read_text()
VERSION = Path('VERSION.txt').read_text().strip()


def test_v325_version():
    assert VERSION == '2026.08.31-354-ADDRESS-READINESS-FIX'


def test_admin_main_area_uses_one_segmented_selector_not_five_columns():
    assert 'st.segmented_control(\n    "Adminområde"' in APP
    assert 'group_cols = st.columns(len(group_names))' not in APP
    assert '_sync_admin_group_selector' in APP


def test_initial_class_creation_is_progressive_and_vertical():
    assert 'with st.expander("➕ Lägg till åldersklass / kategori"' in SETUP
    assert 'add_c1, add_c2, add_c3, add_c4 = st.columns' not in SETUP


def test_existing_class_editing_avoids_five_compressed_columns():
    assert 'c1, c2, c3, c4, c5 = st.columns' not in SETUP
    assert 'with st.container(border=True):' in SETUP
    assert '"Ta bort klass"' in SETUP


def test_sport_profile_is_compact_not_four_metrics():
    assert '_sp1,_sp2,_sp3,_sp4=st.columns(4)' not in SETUP
    assert 'min. lagvila' in SETUP
