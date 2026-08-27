
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")


def test_offer_and_shift_destructive_writes_are_guarded():
    assert "def _admin_update_offer_if_unchanged(" in APP
    assert "def _admin_delete_offer_if_unchanged(" in APP
    assert "def _admin_delete_functionary_shift_if_unchanged(" in APP
    assert "Erbjudandet ändrades av en annan administratör" in APP
    assert "Arbetspasset ändrades av en annan administratör" in APP


def test_portal_code_rotation_uses_credential_snapshot():
    assert "def _rotate_participant_code_if_unchanged(" in APP
    assert "_credential_snapshot(credential)" in APP
    assert "Lagkoden ändrades av en annan administratör" in APP


def test_trash_restore_and_permanent_delete_are_compare_and_set():
    assert "def _trash_tournament_if_current(" in APP
    assert "def _restore_trashed_tournament_if_current(" in APP
    assert "def _delete_trashed_tournament_if_current(" in APP
    assert "Cupen ändrades eller återställdes av en annan administratör" in APP


def test_referee_email_is_validated_before_insert():
    block=APP[APP.index('if admin_page == "Domare":'):APP.index('if admin_page == "Skapa och publicera schema":')]
    assert "Ange en giltig e-postadress eller lämna fältet tomt." in block
