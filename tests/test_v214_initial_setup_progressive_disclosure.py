
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
SETUP=(ROOT/"cupnavi_core"/"initial_setup_view.py").read_text(encoding="utf-8")


def test_changing_room_details_only_render_when_enabled():
    block=SETUP[SETUP.index('cr_toggle=f"setup_changing_rooms_'):SETUP.index('pshow=f"setup_show_prices_')]
    assert "changing_rooms_enabled=st.checkbox(" in block
    assert "if changing_rooms_enabled:" in block
    assert '"Information om omklädningsrum"' in block


def test_price_details_only_render_when_enabled():
    start=SETUP.index('pshow=f"setup_show_prices_')
    end=SETUP.index('st.markdown("### 7. Kontroll & skapa")',start)
    block=SETUP[start:end]
    assert "show_prices_enabled=st.checkbox(" in block
    assert "if show_prices_enabled:" in block
    assert '"Priser/avgifter"' in block


def test_capacity_calculation_is_not_duplicated_inline():
    setup=SETUP
    assert "estimated_capacity_slots(" in setup
    assert "available_pitch_minutes(" in setup
    assert "estimated_match_length_minutes(" in setup
