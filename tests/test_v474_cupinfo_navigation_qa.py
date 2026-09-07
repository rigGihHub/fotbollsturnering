from pathlib import Path

VERSION = "2026.09.07-497-MY-TEAMS-NOTICES-POLISH"
APP = Path("app.py").read_text(encoding="utf-8")
LOGIC = Path("cupnavi_core/public_view_logic.py").read_text(encoding="utf-8")
INFO = Path("cupnavi_core/public_info_view.py").read_text(encoding="utf-8")


def test_version_is_v474():
    assert VERSION in APP
    assert Path("VERSION.txt").read_text().strip() == VERSION


def test_visible_team_nav_is_plural_but_route_stays_compatible():
    assert '("Mitt lag", "team", "Mina lag", "Mina lag")' in LOGIC


def test_cupinfo_prioritizes_organizer_message():
    assert "📣 {tr('Viktig information från arrangören')}" in INFO
    organizer = INFO.index("Viktig information från arrangören")
    rules = INFO.index('with st.expander("📘 " + tr("Cupens regler")')
    assert organizer < rules


def test_rules_are_secondary_but_still_present():
    assert 'with st.expander("📘 " + tr("Cupens regler"), expanded=False):' in INFO
    assert "public_rules_html(tournament, info_rules)" in INFO


def test_practical_info_stays_before_rules():
    practical = INFO.index("cn-practical-info-card")
    rules = INFO.index('with st.expander("📘 " + tr("Cupens regler")')
    assert practical < rules


def test_secondary_details_label_is_shorter():
    assert '"Fler cupdetaljer"' in INFO
