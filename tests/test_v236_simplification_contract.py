
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
TEXT=(ROOT/"app.py").read_text(encoding="utf-8")


def _creation_block():
    start=TEXT.index('def render_new_tournament_creator')
    end=TEXT.index('if view_mode == "Admin":\n    clone_sources', start)
    return TEXT[start:end]


def test_advanced_creation_settings_are_progressively_disclosed():
    block=_creation_block()
    advanced=block.index('with st.expander("Fler alternativ"')
    environment=block.index('environment_type = st.radio(', advanced)
    locale=block.index('create_locale = st.selectbox(', advanced)
    timezone=block.index('create_timezone = st.text_input(', advanced)
    country=block.index('create_country = st.text_input(', advanced)
    assert advanced < environment < locale < timezone < country
    assert 'expanded=os.environ.get("CUPNAVI_E2E") == "1"' in block


def test_normal_creation_flow_defaults_to_one_day():
    block=_creation_block()
    assert 'start_date = st.date_input("Cupdag")' in block
    assert 'multi_day = st.checkbox("Cupen pågår flera dagar"' in block
    assert 'end_date = st.date_input("Sista cupdag", value=start_date) if multi_day else start_date' in block


def test_creation_keeps_locked_international_foundation():
    block=_creation_block()
    for token in [
        '"locale": create_locale',
        '"timezone_name": normalized_timezone',
        '"country_code": create_country or None',
        '"environment_type": environment_type',
    ]:
        assert token in block
