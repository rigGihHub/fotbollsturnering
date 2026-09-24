from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ROLE=(ROOT/"cupnavi_api/role_access_routes.py").read_text(encoding="utf-8")
MAIN=(ROOT/"cupnavi_api/main.py").read_text(encoding="utf-8")
CLIENT=(ROOT/"frontend-next/src/components/reporter-client.tsx").read_text(encoding="utf-8")

def test_reporter_e2e_has_login_session_reporting_and_result_routes():
    for route in (
        '@app.post("/api/reporter/session")',
        '@app.get("/api/reporter/session")',
        '@app.get("/api/reporter/reporting")',
        '@app.put("/api/reporter/reporting/matches/{match_id}")',
    ):
        assert route in ROLE

def test_reporter_result_write_is_explicitly_cup_scoped():
    assert "_require_reporter_match(int(identity[\"tid\"]), match_id)" in ROLE
    assert "save_result(" in ROLE
    assert "int(identity[\"tid\"]), match_id" in ROLE

def test_reporter_code_rotation_invalidates_old_sessions():
    assert '"rev": revision' in ROLE
    assert "hmac.compare_digest(str(payload.get(\"rev\") or \"\"), revision)" in ROLE

def test_reporter_login_is_rate_limited_and_codes_are_hashed():
    assert 'scope="reporter_login"' in ROLE
    assert "_find_reporter_credential(payload.code)" in ROLE
    assert "verify_access_code(code" in ROLE
    assert "code_hash TEXT NOT NULL" in ROLE and "code_salt TEXT NOT NULL" in ROLE

def test_reporter_frontend_uses_narrow_reporter_api_not_admin_result_api():
    assert "/api/reporter/session" in CLIENT
    assert "/api/reporter/reporting" in CLIENT
    assert "/api/admin/cups/" not in CLIENT

def test_public_result_and_standings_routes_exist_for_reporter_feedback_loop():
    assert '@app.get("/api/public/cups/{public_key}")' in MAIN
    assert '@app.get("/api/public/cups/{public_key}/standings")' in MAIN
