from pathlib import Path

VERSION = "2026.09.03-424-PUBLIC-INFO-ROUNDTRIP-CUT"
ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "cupnavi_core" / "public_statistics_view.py").read_text(encoding="utf-8")


def test_version_is_v313():
    assert (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip() == VERSION
    assert f'APP_VERSION = "{VERSION}"' in (ROOT / "cupnavi_core" / "version.py").read_text(encoding="utf-8")
    assert f'APP_BUILD_VERSION = "{VERSION}"' in (ROOT / "app.py").read_text(encoding="utf-8")


def test_final_ranking_calculation_is_gated_by_completed_published_matches():
    block_start = SOURCE.index('if bool(row_value(tournament, "enable_final_ranking", 0)):')
    block_end = SOURCE.index('if stats_section == tr("Topplistor")', block_start)
    block = SOURCE[block_start:block_end]

    done_check = 'all_done = bool(published_matches) and len(played_matches) == len(published_matches)'
    guarded_call = 'if all_done:\n                ranking = final_ranking_rows(tournament_id, tournament)'

    assert done_check in block
    assert guarded_call in block
    assert block.index(done_check) < block.index('ranking = final_ranking_rows(tournament_id, tournament)')


def test_in_progress_tournament_keeps_existing_explanatory_caption():
    assert 'Den slutliga rankingen visas när alla publicerade matcher är färdigspelade.' in SOURCE
