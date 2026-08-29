from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
SETUP=(ROOT/"cupnavi_core"/"initial_setup_view.py").read_text(encoding="utf-8")
R="2026.08.29-301-E2E-PUBLIC-NAVIGATION-CONTRACT"

def setup_block():
    return SETUP

def test_setup_order_is_capacity_first():
    block=setup_block()
    positions=[
        block.index("### 1. Grunduppgifter"),
        block.index("### 2. Kapacitet & speltider"),
        block.index("### 3. Rekommenderat tävlingsformat"),
        block.index("### 4. Tävlingsregler"),
        block.index("### 5. Schemaprioriteringar"),
        block.index("### 6. Arrangemang & deltagarservice"),
        block.index("### 7. Kontroll & skapa"),
    ]
    assert positions==sorted(positions)

def test_capacity_summary_precedes_format_recommendation():
    block=setup_block()
    assert block.index("Uppskattade matchslotar") < block.index("### 3. Rekommenderat tävlingsformat")
    assert "avgör hur många matcher och vilket slutspel som faktiskt ryms" in block

def test_service_questions_are_not_in_sidebar_creation():
    create_start=APP.index('with st.sidebar.expander("Skapa ny turnering")')
    create_end=APP.index('if view_mode == "Matchrapportör"',create_start)
    create=APP[create_start:create_end]
    assert 'st.checkbox("Använd lagincheckning"' not in create
    assert 'st.checkbox("Tillgång till omklädningsrum"' not in create
    block=setup_block()
    assert "Använd lagincheckning" in block
    assert "Skapa slutlig ranking av alla lag" in block
    assert "Visa priser/avgifter publikt" in block

def test_priority_ui_separates_core_and_advanced():
    block=setup_block()
    assert "Grundprioriteringar" in block
    assert "Avancerade schemamål" in block
    assert "_core_priorities" in block
    assert "_advanced_priorities" in block

def test_release_sync():
    assert f'APP_BUILD_VERSION = "{R}"' in APP
    assert f'APP_VERSION = "{R}"' in (ROOT/"cupnavi_core/version.py").read_text(encoding="utf-8")
    assert (ROOT/"VERSION.txt").read_text().strip()==R
