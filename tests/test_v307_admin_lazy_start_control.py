from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "app.py"


def _block() -> str:
    text = APP.read_text(encoding="utf-8")
    start = text.index('with st.expander("Publicering & startkontroll", expanded=False):')
    end = text.index('with st.expander("⚠️ Riskzon – Cup och papperskorg", expanded=False):', start)
    return text[start:end]


def test_start_control_is_opt_in_and_avoids_heavy_queries():
    block = _block()
    toggle = block.index('st.toggle(')
    guard = block.index('if _show_start_control:')
    assert toggle < guard
    assert 'workflow_counts["scheduled_n"]' in block[guard:]
    assert 'SELECT * FROM groups WHERE tournament_id=?' not in block[guard:]
    assert 'SELECT * FROM teams WHERE tournament_id=?' not in block[guard:]
    assert 'SELECT * FROM matches WHERE tournament_id=?' not in block[guard:]


def test_start_control_preserves_existing_readiness_checks():
    block = _block()
    for label in (
        "Minst en grupp är skapad",
        "Minst ett lag är registrerat",
        "Alla lag är placerade i en grupp",
        "Alla matcher som kan planeras har en schematid",
        "Alla schemalagda matcher har domare",
        "Det aktuella schemat är godkänt och publicerat",
    ):
        assert label in block


def test_release_version_is_v307():
    version = (APP.parent / "VERSION.txt").read_text(encoding="utf-8").strip()
    assert version == "2026.09.03-414-PITCH-TIMING-MODE"
