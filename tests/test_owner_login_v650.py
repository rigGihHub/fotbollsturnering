import os

from cupnavi_api.admin_auth import (
    OWNER_ACCOUNT_ID,
    authenticate_owner,
    issue_session,
    owner_identity,
    verify_session,
)


def test_owner_login_requires_both_environment_secrets(monkeypatch):
    monkeypatch.delenv("CUPNAVI_OWNER_EMAIL", raising=False)
    monkeypatch.delenv("CUPNAVI_OWNER_PASSWORD", raising=False)
    assert owner_identity() is None
    assert authenticate_owner("owner@cupnavi.local", "secret") is None


def test_owner_login_is_exact_and_constant_contract(monkeypatch):
    monkeypatch.setenv("CUPNAVI_OWNER_EMAIL", "Owner@CupNavi.Local")
    monkeypatch.setenv("CUPNAVI_OWNER_PASSWORD", "correct-horse-battery-staple")
    owner = authenticate_owner("owner@cupnavi.local", "correct-horse-battery-staple")
    assert owner is not None
    assert owner["id"] == OWNER_ACCOUNT_ID
    assert owner["role"] == "owner"
    assert authenticate_owner("owner@cupnavi.local", "wrong") is None
    assert authenticate_owner("other@cupnavi.local", "correct-horse-battery-staple") is None


def test_owner_session_round_trip_requires_owner_to_remain_configured(monkeypatch):
    monkeypatch.setenv("CUPNAVI_OWNER_EMAIL", "owner@cupnavi.local")
    monkeypatch.setenv("CUPNAVI_OWNER_PASSWORD", "owner-secret")
    monkeypatch.setenv("CUPNAVI_SESSION_SECRET", "session-secret")
    owner = authenticate_owner("owner@cupnavi.local", "owner-secret")
    token = issue_session(owner)
    payload = verify_session(token)
    assert payload is not None
    assert payload["sub"] == OWNER_ACCOUNT_ID
    assert payload["role"] == "owner"

    monkeypatch.delenv("CUPNAVI_OWNER_PASSWORD", raising=False)
    assert verify_session(token) is None
