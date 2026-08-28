from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
BACKUP=(ROOT/"cupnavi_core/backup.py").read_text(encoding="utf-8")
R="2026.08.28-254-PUBLISH-EMPTY-STATE-FIX"

def test_restore_is_non_destructive():
    assert "restore_backup_as_new_tournament" in BACKUP
    assert "Originalcupen skrivs aldrig över" in BACKUP
    assert "Återställ som ny cup" in APP

def test_backup_format_v2_and_legacy_validation():
    assert "BACKUP_FORMAT_VERSION = 2" in BACKUP
    assert "version not in (1, BACKUP_FORMAT_VERSION)" in BACKUP

def test_backup_is_more_complete():
    for name in ("competition_classes","pitch_day_windows","schedule_requests","match_rosters","functionary_shifts","team_messages","participant_access_credentials","notification_subscriptions","control_incidents"):
        assert f'"{name}"' in APP

def test_restore_remaps_relationships():
    for mapping in ("class_map","group_map","team_map","player_map","referee_map","bracket_map","match_map"):
        assert mapping in BACKUP
    assert "def _map_source" in BACKUP

def test_rollback_runbook_exists():
    assert (ROOT/"ROLLBACK.md").exists()

def test_version():
    assert "Version v.1.254" in APP
    assert f'APP_BUILD_VERSION = "{R}"' in APP
