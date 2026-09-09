import json

from cupnavi_core.backup import build_backup_bytes, validate_backup_bytes


def test_backup_roundtrip():
    data, checksum = build_backup_bytes(
        "test-version",
        7,
        {"teams": [{"id": 1, "name": "Lag A"}]},
    )
    assert len(checksum) == 64
    payload = validate_backup_bytes(data)
    assert payload["tournament_id"] == 7
    assert payload["data"]["teams"][0]["name"] == "Lag A"


def test_backup_is_utf8_json():
    data, _ = build_backup_bytes(
        "test",
        1,
        {"teams": [{"name": "Örebro SK"}]},
    )
    decoded = json.loads(data.decode("utf-8"))
    assert decoded["data"]["teams"][0]["name"] == "Örebro SK"
