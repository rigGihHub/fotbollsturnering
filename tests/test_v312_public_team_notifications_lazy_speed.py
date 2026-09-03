from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / "cupnavi_core" / "public_team_follow_view.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()


def test_release_version():
    assert VERSION == "2026.09.03-423-PUBLIC-INFO-COLD-START"


def test_notification_history_query_is_explicitly_lazy():
    gate = SRC.index('show_notification_history = st.toggle(')
    guarded = SRC.index('if show_notification_history:', gate)
    query = SRC.index('SELECT * FROM notifications WHERE tournament_id=?', guarded)
    assert gate < guarded < query


def test_notification_history_has_clear_opt_in_and_empty_state():
    assert '"🔔 Visa senaste lagnotiser"' in SRC
    assert 'Inga lagnotiser har publicerats ännu.' in SRC


def test_notification_subscription_form_remains_available_before_lazy_history():
    subscription = SRC.index('with st.expander("🔔 Få viktiga lagnotiser via e-post"')
    create = SRC.index('create_notification_subscription(', subscription)
    gate = SRC.index('show_notification_history = st.toggle(', create)
    assert subscription < create < gate
