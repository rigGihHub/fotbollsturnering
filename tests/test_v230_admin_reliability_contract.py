
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")


def test_sponsor_and_functionary_writes_use_snapshot_helpers():
    assert "def _admin_update_sponsor_if_unchanged(" in APP
    assert "def _admin_delete_sponsor_if_unchanged(" in APP
    assert "def _admin_update_functionary_if_unchanged(" in APP
    assert "def _admin_delete_functionary_if_unchanged(" in APP
    assert "Sponsorn ändrades av en annan administratör" in APP
    assert "Funktionären ändrades av en annan administratör" in APP


def test_publish_unpublish_use_compare_and_set_helper():
    assert "def _set_publication_if_current(" in APP
    assert "expected_lifecycle=tournament_lifecycle" in APP
    assert "Publiceringsstatusen ändrades av en annan administratör" in APP


def test_lifecycle_buttons_use_guarded_transition():
    assert "def _set_lifecycle_if_current(" in APP
    assert '"published",\n            "live"' in APP
    assert '"completed"' in APP


def test_audit_undo_is_one_transaction_helper():
    assert "def _undo_audit_entry_if_current(" in APP
    block=APP[APP.index('st.subheader("↩️ Ändringshistorik och ångra")'):]
    assert "_undo_audit_entry_if_current(" in block
    assert 'run("UPDATE audit_log SET undone_at=? WHERE id=?")' not in block
