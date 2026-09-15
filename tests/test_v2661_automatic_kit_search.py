from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_kit_search_uses_configurable_api_model_instead_of_agent_model():
    api=(ROOT/"cupnavi_api/main.py").read_text()
    kit=(ROOT/"cupnavi_core/ai_kit_suggestion.py").read_text()
    assert "CUPNAVI_AI_KIT_MODEL" in api
    assert 'model="gpt-4.1-mini"' in kit
    assert "gpt-5.6-luna" not in kit

def test_verified_result_is_inserted_into_form_automatically():
    ui=(ROOT/"frontend-next/src/components/admin-workspace.tsx").read_text()
    block=ui[ui.index("async function searchKit"):ui.index("function applyKitSuggestion")]
    for field in ("primary_color","home_color_2","home_pattern","secondary_color","away_color_2","away_pattern"):
        assert field in block
    assert "Verifierade tröjfärger och mönster har fyllts i" in block
