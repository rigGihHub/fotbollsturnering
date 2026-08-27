
from pathlib import Path
import ast

ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
MIG=(ROOT/"cupnavi_core/migrations.py").read_text(encoding="utf-8")


def _portal():
    tree=ast.parse(APP)
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="render_team_portal")
    lines=APP.splitlines()
    return "\n".join(lines[node.lineno-1:node.end_lineno])


def test_checkin_and_kit_use_conditional_helpers():
    portal=_portal()
    assert "_set_team_checkin_if_unchanged(" in portal
    assert "_confirm_team_kit_if_unchanged(" in portal
    assert 'disabled=bool(team_row["kit_confirmed_at"])' in portal


def test_message_forms_use_request_tokens():
    portal=_portal()
    assert "portal_message_request_token_" in portal
    assert "request_token=st.session_state[portal_message_token_key]" in portal
    assert "admin_message_request_token_" in APP
    assert "admin_reply_request_token_" in APP


def test_message_schema_has_unique_request_token():
    assert "request_token" in APP
    assert "idx_team_messages_request_token" in APP
    assert "idx_team_messages_request_token" in MIG


def test_sent_messages_show_email_notification_state():
    portal=_portal()
    assert "E-postnotis skickad" in portal
    assert "Ingen e-postadress registrerad" in portal
