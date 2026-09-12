from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_public_frontend_hydrates_resolution_sidecar_without_api_contract_change():
    api = _read("frontend-next/src/lib/api.ts")
    assert "participant_resolution" in api
    assert "home_participant:resolved.home" in api
    assert "away_participant:resolved.away" in api
    assert "hydrateParticipants(cup)" in api


def test_match_card_prefers_resolved_team_names_and_keeps_human_fallbacks():
    card = _read("frontend-next/src/components/MatchCard.tsx")
    fmt = _read("frontend-next/src/lib/format.ts")
    assert "match.home_participant" in card
    assert "match.away_participant" in card
    assert "participantLabel" in card
    assert 'parts[0]==="group"' in fmt
    assert 'Vinnare match' in fmt
    assert 'Förlorare match' in fmt


def test_admin_playoff_hides_raw_symbolic_sources_from_primary_match_label():
    admin = _read("frontend-next/src/components/playoff-admin.tsx")
    assert 'participantLabel(m,"home")' in admin
    assert 'participantLabel(m,"away")' in admin
    assert "home_team_name" in admin
    assert "away_team_name" in admin
    assert '{m.home_source||"Ej satt"} – {m.away_source||"Ej satt"}' not in admin


def test_v647_version_is_canonical():
    expected = "2026.09.12-647-PARTICIPANT-UI"
    assert (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip() == expected
    assert f'APP_VERSION = "{expected}"' in _read("cupnavi_core/version.py")
