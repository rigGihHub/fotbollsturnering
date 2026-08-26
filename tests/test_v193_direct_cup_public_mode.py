from pathlib import Path
APP=(Path(__file__).resolve().parents[1]/"app.py").read_text(encoding="utf-8")

def test_fresh_direct_cup_link_forces_public_view():
    assert '_direct_public_cup = bool(str(st.query_params.get("cup", "")).strip())' in APP
    marker=APP.index("if _direct_public_cup and st.session_state.get")
    block=APP[marker:marker+500]
    assert 'st.session_state["view_mode"] = "Turneringsvy"' in block
    assert block.index('"Turneringsvy"') < block.index("mode_options[0]")
