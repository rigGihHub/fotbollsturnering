
from pathlib import Path

APP=(Path(__file__).resolve().parents[1]/"app.py").read_text(encoding="utf-8")


def test_changing_room_details_only_render_when_enabled():
    block=APP[APP.index('cr_toggle=f"setup_changing_rooms_'):APP.index('pshow=f"setup_show_prices_')]
    assert "changing_rooms_enabled=st.checkbox(" in block
    assert "if changing_rooms_enabled:" in block
    assert '"Information om omklädningsrum"' in block


def test_price_details_only_render_when_enabled():
    start=APP.index('pshow=f"setup_show_prices_')
    end=APP.index('st.markdown("### 7. Kontroll & skapa")',start)
    block=APP[start:end]
    assert "show_prices_enabled=st.checkbox(" in block
    assert "if show_prices_enabled:" in block
    assert '"Priser/avgifter"' in block


def test_capacity_calculation_is_not_duplicated_inline():
    setup=APP[APP.index("def render_initial_tournament_setup"):APP.index("def _render_with_friendly_error")]
    assert "estimated_capacity_slots(" in setup
    assert "available_pitch_minutes(" in setup
    assert "estimated_match_length_minutes(" in setup
