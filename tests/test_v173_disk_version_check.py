from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
FOLLOW_VIEW=(ROOT/"cupnavi_core"/"public_team_follow_view.py").read_text(encoding="utf-8")
R="2026.09.07-505-ADMIN-PREVIEW-CODES-SETTINGS"

def test_version_check_reads_deployed_file_directly():
    assert "def read_core_version_from_disk" in APP
    assert 'Path(__file__).resolve().parent / "cupnavi_core" / "version.py"' in APP
    assert "CORE_APP_VERSION = read_core_version_from_disk()" in APP
    assert "IMPORTED_CORE_APP_VERSION" in APP

def test_release_mismatch_uses_disk_version():
    assert "RELEASE_FILES_MISMATCH = CORE_APP_VERSION != APP_BUILD_VERSION" in APP
    assert "Kontrollen läser versionsfilen direkt från den deployade disken." in APP

def test_public_team_selector_uses_explicit_all_teams_sentinel():
    assert '_favorites_key = f"public_favorite_teams_{tournament_id}"' in FOLLOW_VIEW
    assert 'team_id in team_ids' in FOLLOW_VIEW
    assert 'active_team_id = int(requested_team_id) if requested_team_id in favorite_team_ids else int(favorite_team_ids[0])' in FOLLOW_VIEW

def test_release_sync():
    assert f'APP_BUILD_VERSION = "{R}"' in APP
    assert f'APP_VERSION = "{R}"' in (ROOT/"cupnavi_core/version.py").read_text(encoding="utf-8")
    assert (ROOT/"VERSION.txt").read_text().strip()==R
