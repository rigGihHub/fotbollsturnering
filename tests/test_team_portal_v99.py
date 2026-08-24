from datetime import datetime, timedelta
from pathlib import Path

from cupnavi_core.team_portal import (
    generate_access_code,
    new_code_hash,
    verify_access_code,
    squad_deadline_at,
    squad_is_locked,
)


def test_team_codes_are_random_hashable_and_case_insensitive():
    code = generate_access_code()
    assert len(code) == 6
    salt, digest = new_code_hash(code)
    assert code not in digest
    assert verify_access_code(code.lower(), salt, digest)
    assert not verify_access_code("AAAAAA", salt, digest)


def test_match_squad_deadline_locking():
    start = "2026-08-24T10:00:00"
    assert squad_deadline_at(start, 30) == datetime(2026, 8, 24, 9, 30)
    assert not squad_is_locked(start, 30, now=datetime(2026, 8, 24, 9, 29))
    assert squad_is_locked(start, 30, now=datetime(2026, 8, 24, 9, 30))


def test_app_contains_restricted_team_portal_flows():
    text = Path("app.py").read_text(encoding="utf-8")
    assert '"Lagportal"' in text
    assert "def render_team_portal(" in text
    assert "participant_access_credentials" in text
    assert "match_rosters" in text
    assert "Kopiera föregående matchtrupp" in text
    assert "Matchtrupp ej registrerad" in text
    assert "Endast dessa kan få matchhändelser" in text
    assert "allow_team_public_contact" in text


def test_schema_version_is_six_for_team_portal():
    text = Path("cupnavi_core/migrations.py").read_text(encoding="utf-8")
    assert "LATEST_SCHEMA_VERSION = 7" in text
    assert '"participant_team_portal_v99"' in text
