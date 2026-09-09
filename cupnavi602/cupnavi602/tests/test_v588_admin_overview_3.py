from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / 'app.py').read_text(encoding='utf-8')


def _overview_block():
    start = APP.index('elif admin_page == "Adminöversikt":')
    end = APP.index('if admin_page == "Cupinställningar":', start)
    return APP[start:end]


def test_overview_first_screen_answers_three_questions():
    block = _overview_block()
    assert 'Var står cupen?' in block
    assert 'Vad behöver jag göra nu?' in block
    assert 'Vad blockerar?' in block
    assert 'decision.action_label + " →"' in block


def test_only_primary_blocker_is_expanded_by_default():
    block = _overview_block()
    assert 'decision.missing[0]' in block
    assert 'with st.expander(f"Visa alla {len(decision.missing)} kvarvarande steg", expanded=False):' in block
    assert 'decision.missing[1:]' in block


def test_revision_import_and_operational_attention_are_progressively_disclosed():
    block = _overview_block()
    assert 'with st.expander("Snabbverktyg", expanded=False):' in block
    assert '"🔄 Ny eller ändrad PDF / foto"' in block
    assert 'with st.expander(f"Kräver din uppmärksamhet · {len(attention)}", expanded=False):' in block


def test_advanced_overview_does_not_duplicate_step_guide():
    block = _overview_block()
    assert '#### Analys & drift' in block
    assert 'key=f"v588_quick_guide_{tid}"' in block
    assert 'key=f"v341_open_guide_{tid}"' not in block


def test_v588_version_is_synchronized():
    version = '2026.09.09-588-ADMIN-OVERVIEW-3'
    assert version in APP
    assert (ROOT / 'VERSION.txt').read_text(encoding='utf-8').strip() == version
    assert version in (ROOT / 'cupnavi_core' / 'version.py').read_text(encoding='utf-8')
