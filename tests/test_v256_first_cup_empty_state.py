from pathlib import Path
APP=(Path(__file__).resolve().parents[1]/"app.py").read_text(encoding="utf-8")

def test_empty_admin_state_is_device_neutral_and_actionable():
    block=APP[APP.index("if not tournaments:"):APP.index("# Resolve cup= against the actual accessible rows")]
    assert '"Skapa din första cup"' in block
    assert '"Öppna sidomenyn (☰ på mobil) och välj Skapa ny turnering.' in block
    assert 'Du behöver bara namn, spelort, sport och cupdag' in block
    assert 'Skapa den första turneringen i vänstermenyn.' not in block

def test_empty_state_uses_keyword_only_symbol_contract():
    block=APP[APP.index("if not tournaments:"):APP.index("# Resolve cup= against the actual accessible rows")]
    assert 'symbol="🏆"' in block
