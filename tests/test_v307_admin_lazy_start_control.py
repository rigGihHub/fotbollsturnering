from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "app.py"


def _block() -> str:
    text = APP.read_text(encoding="utf-8")
    start = text.index('with st.expander("Publicering & startkontroll", expanded=False):')
    end = text.index('with st.expander("⚠️ Riskzon – Cup och papperskorg", expanded=False):', start)
    return text[start:end]


def test_start_control_is_opt_in_before_heavy_queries():
    block = _block()
    toggle = block.index('st.toggle(')
    guard = block.index('if _show_start_control:')
    groups_query = block.index('SELECT * FROM groups WHERE tournament_id=?')
    teams_query = block.index('SELECT * FROM teams WHERE tournament_id=?')
    matches_query = block.index('SELECT * FROM matches WHERE tournament_id=?')
    assert toggle < guard < groups_query < teams_query < matches_query


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
    assert version == "2026.08.31-348-GUIDED-CUP-SETUP"
