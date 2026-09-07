from pathlib import Path

VERSION = "2026.09.07-519-BEGINNER-E2E-REGRESSION"
APP = Path("app.py").read_text(encoding="utf-8")


def test_version_is_v461():
    assert VERSION in APP
    assert Path("VERSION.txt").read_text().strip() == VERSION


def test_operational_pulse_is_above_readiness_detail():
    pulse = APP.index('class="cn-day-kpis"')
    readiness = APP.index("Inför nästa avspark", pulse)
    assert pulse < readiness


def test_operational_pulse_prioritizes_live_problems_next():
    block = APP[APP.index('class="cn-day-kpis"'):APP.index("if _day_readiness:")]
    assert "Pågår nu" in block
    assert "Problem" in block
    assert "Nästa 45 min" in block


def test_readiness_shows_only_primary_risk_open():
    assert "_primary_risk = _day_readiness[0]" in APP
    assert 'with st.expander(f"Visa {len(_day_readiness) - 1} fler beredskapspunkter", expanded=False):' in APP


def test_pitch_focus_is_collapsed_on_mobile_first_home():
    assert 'with st.expander(f"Planer just nu · {len(_day_snapshot[\'pitch_states\'])}", expanded=False):' in APP


def test_no_duplicate_legacy_kpi_block_remains():
    assert '<span class="label">Spelas nu</span>' not in APP
    assert '<span class="label">Inom 45 min</span>' not in APP
