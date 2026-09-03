from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
STYLE = (ROOT / "cupnavi_core" / "style_system.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()


def test_release_version():
    assert VERSION == "2026.09.03-423-PUBLIC-INFO-COLD-START"


def test_cupday_uses_custom_operational_header():
    section = APP[APP.index('if admin_page == "Cupdagen":'):APP.index('if admin_page == "Cupverktyg":')]
    assert 'class="cn-admin-page-head"' in section
    assert "Matchdag · Mobil kontrollcentral" in section
    assert "<h1>Cupdagen</h1>" in section


def test_primary_guidance_has_visual_state_card():
    section = APP[APP.index('if admin_page == "Cupdagen":'):APP.index('if admin_page == "Cupverktyg":')]
    assert 'class="cn-day-guide is-' in section
    assert 'class="eyebrow"' in section
    assert 'class="title"' in section
    assert 'class="detail"' in section
    assert 'type="primary"' in section


def test_operational_kpis_are_compact_custom_cards():
    section = APP[APP.index('if admin_page == "Cupdagen":'):APP.index('if admin_page == "Cupverktyg":')]
    assert 'class="cn-day-kpis"' in section
    assert "Spelas nu" in section
    assert "Inom 45 min" in section
    assert "Behöver åtgärd" in section
    assert '_d1.metric("Nu"' not in section


def test_autopilot_has_secondary_visual_identity():
    section = APP[APP.index('if admin_page == "Cupdagen":'):APP.index('if admin_page == "Cupverktyg":')]
    assert 'class="cn-autopilot-head"' in section
    assert 'class="cn-autopilot-badge">Beslutsstöd' in section


def test_style_system_has_admin_operational_components_and_mobile_rules():
    for marker in (
        ".cn-admin-page-head{",
        ".cn-day-guide{",
        ".cn-day-kpis{",
        ".cn-day-kpi{",
        ".cn-section-head{",
        ".cn-autopilot-head{",
    ):
        assert marker in STYLE
    assert "@media(max-width:768px)" in STYLE
    assert ".cn-day-guide{padding:14px 14px 13px" in STYLE


def test_existing_cupday_progressive_disclosure_remains():
    section = APP[APP.index('if admin_page == "Cupdagen":'):APP.index('if admin_page == "Cupverktyg":')]
    assert 'with st.expander("Planstatus", expanded=False)' in section
    assert 'with st.expander("Fler åtgärder", expanded=False)' in section
    assert 'Senare idag · {len(_later_matches)} matcher' in section
