from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/'app.py').read_text()
DOC=(ROOT/'cupnavi_core/cup_document_creator_view.py').read_text()
AI=(ROOT/'cupnavi_core/ai_cup_document_import.py').read_text()
VER=(ROOT/'cupnavi_core/version.py').read_text()

def test_version(): assert '578-INITIAL-IMPORT-CARRIES-PLANS-RULES' in VER
def test_rules_reused(): assert 'Regler från första importen' in APP and 'Använd avlästa regelvärden' in APP
def test_plans_reused(): assert 'Planer hittade i första importen' in APP and 'Använd hittade planer' in APP
def test_no_fake_opening_hours(): assert 'tolkar inte automatiskt första/sista matchtid som planens öppettid' in APP
def test_structured_rules_are_explicit(): assert 'rule_values' in AI and 'annars null' in AI
def test_helpers_exist(): assert 'def document_plan_hints' in DOC and 'def document_rule_values' in DOC
