import json
from pathlib import Path

from cupnavi_core.ai_cup_document_import import extract_cup_setup_from_documents

ROOT = Path(__file__).resolve().parents[1]


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_existing_cup_has_review_first_photo_pdf_import_tool():
    importer = (ROOT / "frontend-next/src/components/document-import-admin.tsx").read_text(encoding="utf-8")
    host = (ROOT / "frontend-next/src/components/import-admin.tsx").read_text(encoding="utf-8")

    assert "DocumentImportAdmin" in host
    assert "Läs in foto/PDF till aktiv cup" in importer
    assert "/api/admin/cup-import/analyze" in importer
    assert "/import/initial" in importer
    assert "Spara till aktiv cup" in importer
    assert "GRANSKA FÖRST" in importer


def test_existing_cup_document_import_preserves_existing_data():
    importer = (ROOT / "frontend-next/src/components/document-import-admin.tsx").read_text(encoding="utf-8")

    assert "team.group_id && team.group_id !== groupId" in importer
    assert "flyttades inte" in importer
    assert "schedule.match_count === 0" in importer
    assert "redan har matcher" in importer
    assert "defaultPitchName" in importer
    assert "skrevs inte över" in importer
    assert "completed_count" in importer


def test_pdf_import_error_is_actionable_instead_of_raw_http_400():
    core = (ROOT / "cupnavi_core/ai_cup_document_import.py").read_text(encoding="utf-8")
    importer = (ROOT / "frontend-next/src/components/document-import-admin.tsx").read_text(encoding="utf-8")

    assert "HTTPError" in core
    assert "Prova att exportera PDF:en på nytt" in core
    assert "friendlyAnalyzeError" in importer
    assert "HTTP Error 400|Bad Request" in importer


def test_multi_document_pdf_is_sent_as_data_url_file_input():
    seen = {}
    output = {
        "tournament_name": "Cup",
        "location": None,
        "start_date": None,
        "end_date": None,
        "venues": [],
        "pitch_windows": [],
        "teams": [],
        "matches": [],
        "playoff_matches": [],
        "rules": [],
        "rule_values": {
            "halves": None,
            "minutes_per_half": None,
            "halftime_minutes": None,
            "points_win": None,
            "points_draw": None,
            "points_loss": None,
        },
        "playoff_rule_values": {
            "halves": None,
            "minutes_per_half": None,
            "halftime_minutes": None,
            "pitch_break_minutes": None,
            "tie_rule": None,
            "extra_time_minutes": None,
        },
        "warnings": [],
    }
    payload = {"output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(output)}]}]}

    def opener(request, **kwargs):
        seen["body"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse(payload)

    extract_cup_setup_from_documents([(b"%PDF-test", "schema.pdf", "application/pdf")], "x", opener=opener)
    files = [part for part in seen["body"]["input"][0]["content"] if part.get("type") == "input_file"]
    assert files
    assert files[0]["file_data"].startswith("data:application/pdf;base64,")


def test_admin_uses_persistent_verified_session_cache_to_stop_mobile_bounce():
    shell = (ROOT / "frontend-next/src/components/admin-auth-shell.tsx").read_text(encoding="utf-8")
    gate = (ROOT / "frontend-next/src/lib/admin-session-fetch-gate.ts").read_text(encoding="utf-8")
    operations = (ROOT / "frontend-next/src/components/admin-operations.tsx").read_text(encoding="utf-8")

    for source in (shell, gate, operations):
        assert "cupnavi_admin_verified_persistent_v1" in source
    assert "localStorage.setItem(VERIFIED_PERSISTENT_CACHE_KEY" in shell
    assert "localStorage.removeItem(VERIFIED_PERSISTENT_CACHE_KEY" in shell
    assert "VERIFIED_PERSISTENT_CACHE_KEY" in gate
