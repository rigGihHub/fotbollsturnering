from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROLE = (ROOT / "cupnavi_api/role_access_routes.py").read_text(encoding="utf-8")


def test_reporter_session_lasts_48_hours():
    assert "MAX_REPORTER_SESSION_SECONDS = 60 * 60 * 24 * 7" in ROLE
    assert "valid_hours INTEGER NOT NULL DEFAULT 48" in ROLE
    assert "min(MAX_REPORTER_SESSION_SECONDS, max(1, int(valid_hours)) * 60 * 60)" in ROLE


def test_reporter_session_is_invalidated_when_code_rotates():
    assert '"rev": revision' in ROLE
    assert 'row = _credential(int(payload["tid"]))' in ROLE
    assert 'hmac.compare_digest(str(payload.get("rev") or ""), revision)' in ROLE


def test_reporter_match_routes_enforce_tournament_scope():
    assert "def _require_reporter_match" in ROLE
    assert 'SELECT 1 AS ok FROM matches WHERE id=? AND tournament_id=?' in ROLE
    # Result, lifecycle status, event read and player-event write must each
    # perform the explicit match-to-cup check before delegating to admin logic.
    assert ROLE.count('_require_reporter_match(int(identity["tid"]), match_id)') >= 4


def test_reporter_login_is_rate_limited_and_code_is_not_plaintext():
    assert 'scope="reporter_login"' in ROLE
    assert "verify_access_code(payload.code" in ROLE
    assert "code_hash TEXT NOT NULL" in ROLE
    assert "code_salt TEXT NOT NULL" in ROLE
