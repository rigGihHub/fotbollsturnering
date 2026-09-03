from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WIZARD = (ROOT / "cupnavi_core" / "new_tournament_wizard.py").read_text(encoding="utf-8")
INFO = (ROOT / "cupnavi_core" / "public_info_view.py").read_text(encoding="utf-8")
MIGRATIONS = (ROOT / "cupnavi_core" / "migrations.py").read_text(encoding="utf-8")


def test_pitch_size_is_required_in_pitch_step_and_uses_supported_formats():
    assert '"5-manna", "7-manna", "9-manna", "11-manna"' in WIZARD
    assert 'pitch_size_format' in WIZARD
    assert 'can_next=valid and unverified == 0 and _pitch_size != "Välj planstorlek"' in WIZARD

def test_public_info_displays_pitch_size():
    assert "<small>Planstorlek</small>" in INFO
    assert 'row_value(info_rules, "pitch_size_format", "")' in INFO

def test_redundant_matchcamp_recommendation_copy_is_removed():
    assert "Det motsvarar cirka {recommendation['estimated_matches']} matcher" not in WIZARD
    assert "Sätt {recommendation['matches_per_team']} matcher per lag" in WIZARD

def test_schema_has_v31_pitch_size_migration():
    assert "LATEST_SCHEMA_VERSION = 31" in MIGRATIONS
    assert "ensure_v31_schema_compat" in MIGRATIONS
