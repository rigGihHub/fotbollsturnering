from pathlib import Path

from cupnavi_core.ai_kit_suggestion import _identities_compatible, _search_strategies


ROOT = Path(__file__).resolve().parents[1]


def test_identity_merge_does_not_mix_same_named_clubs_from_different_places():
    assert _identities_compatible("aik solna", "aik solna fotboll")
    assert not _identities_compatible("aik solna", "aik härnösand")
    assert not _identities_compatible("ifk göteborg", "ifk norrköping")


def test_search_instructions_require_visual_current_kit_evidence():
    _, instruction = _search_strategies("AIK P2014", search_focus="kit")[0]
    assert "själva tröjan" in instruction
    assert "senaste relevanta säsongen" in instruction
    assert "klubbens färger" in instruction


def test_new_kit_patterns_are_available_for_non_striped_designs():
    source = (ROOT / "cupnavi_core/ai_kit_suggestion.py").read_text(encoding="utf-8")
    ui = (ROOT / "frontend-next/src/components/admin-workspace.tsx").read_text(encoding="utf-8")
    assert "Diagonala ränder" in source and "Grafiskt" in source
    assert '"Diagonala ränder"' in ui and '"Grafiskt"' in ui
