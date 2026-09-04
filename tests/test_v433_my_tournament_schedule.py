from pathlib import Path


def test_v433_personal_schedule_contract():
    source = Path("cupnavi_core/public_team_follow_view.py").read_text(encoding="utf-8")
    assert "Min cup · kommande matcher" in source
    assert "Ditt personliga schema" in source
    assert '"Nästa · " if _index == 0' in source
    assert "public_pitch_label(_match)" in source


def test_v433_release_note_exists():
    assert Path("GOTHIA_INSPIRED_MY_TOURNAMENT_V433.md").exists()
