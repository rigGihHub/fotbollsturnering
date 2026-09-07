from pathlib import Path

VERSION = "2026.09.07-505-ADMIN-PREVIEW-CODES-SETTINGS"
APP = Path("app.py").read_text(encoding="utf-8")


def test_version_is_v484():
    assert VERSION in APP
    assert Path("VERSION.txt").read_text().strip() == VERSION


def test_admin_control_has_emergency_pack():
    assert "🧯 Cupdagens nödpaket" in APP
    assert "Backup i denna session" in APP
    assert "Senast förberedd" in APP


def test_emergency_instructions_prevent_double_write():
    assert "Tryck inte flera gånger på samma resultat/mål" in APP
    assert "läs om från servern först" in APP
    assert "Registrera bara sådant som" in APP
    assert "saknas på servern" in APP


def test_no_local_fallback_is_recommended():
    assert "CupNavi byter inte automatiskt till lokal databas" in APP


def test_backup_timestamp_is_recorded():
    assert 'st.session_state[f"backup_created_at_{tid}"] = datetime.now().isoformat(timespec="seconds")' in APP
    assert "Nästa steg: ladda ner JSON-filen" in APP


def test_restore_remains_non_destructive():
    assert "Originalcupen skrivs aldrig över" in APP
    assert "återställ som en ny Testmiljö först" in APP
