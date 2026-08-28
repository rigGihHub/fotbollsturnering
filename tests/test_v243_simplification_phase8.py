
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")


def _block(start_marker,end_marker):
    start=APP.index(start_marker)
    end=APP.index(end_marker,start)
    return APP[start:end]


def test_visitor_stats_keeps_metrics_primary_and_details_collapsed():
    block=_block('if admin_page == "Besöksstatistik":','if admin_page == "Sponsorer":')
    assert 'm1.metric("Unika sessioner", unique_sessions)' in block
    assert 'with st.expander("Utveckling över tid", expanded=False)' in block
    assert 'with st.expander("Enheter, webbläsare & trafikkällor", expanded=False)' in block
    assert 'with st.expander("Senaste besök & integritet", expanded=False)' in block


def test_cup_tools_preserve_operational_actions():
    block=_block('if admin_page == "Cupverktyg":','if admin_page == "Tabeller":')
    assert '"Status", "Flytta match", "Försening"' in block
    assert 'analyze_schedule_change(' in block
    assert 'planned_delay_updates(' in block
    assert 'record_audit(' in block
    assert 'with st.expander("Förhandsvisa ändrade tider", expanded=False)' in block


def test_cup_tools_secondary_detail_is_collapsed():
    block=_block('if admin_page == "Cupverktyg":','if admin_page == "Tabeller":')
    assert 'with st.expander(f"Förbättringspunkter · {len(quality_findings)}", expanded=False)' in block
    assert 'with st.expander("Visa eller ta bort platser", expanded=False)' in block
    assert 'with st.expander("Visa historik & ångra", expanded=False)' in block


def test_leaderboards_keep_goals_primary_and_secondary_stats_collapsed():
    block=_block('if admin_page == "Skytteligor":','if admin_page == "Slutspel":')
    assert 'st.header("Topplistor")' in block
    assert 'st.subheader(tr("Skytteliga"))' in block
    assert 'with st.expander(tr("Assistliga"), expanded=False)' in block
    assert 'with st.expander("Gula/röda kort", expanded=False)' in block
