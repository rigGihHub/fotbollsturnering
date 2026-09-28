import base64
import json

import pytest

from cupnavi_api.admin_repository import _organizer_logos_json
from cupnavi_api.repository import _public_tournament_projection
from cupnavi_api.organizer_logo_repository import get_organizer_logo, save_organizer_logo


def test_organizer_logos_are_validated_and_exposed_to_public_cup():
    logos = [{"name": "Arrangör A", "url": "https://example.org/a.png"}, {"name": "Arrangör B", "url": "https://example.org/b.png"}]
    stored = _organizer_logos_json(logos)
    assert json.loads(stored) == logos
    assert _public_tournament_projection({"id": 1, "name": "Cup", "organizer_logos_json": stored})["organizer_logos"] == logos
    assert _public_tournament_projection({"id": 2, "name": "Äldre cup"})["organizer_logos"] == []


@pytest.mark.parametrize("logos", [
    [{"name": "X", "url": "javascript:alert(1)"}],
    [{"name": "X", "url": "http://example.org/a.png"}],
    [{"name": "", "url": "https://example.org/a.png"}],
    [{"name": "X", "url": "https://example.org/a.png"}] * 4,
])
def test_invalid_banner_logos_are_rejected(logos):
    with pytest.raises(ValueError):
        _organizer_logos_json(logos)


def test_uploaded_logo_survives_a_new_database_connection(tmp_path, monkeypatch):
    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
    monkeypatch.delenv("TURSO_AUTH_TOKEN", raising=False)
    monkeypatch.setenv("CUPNAVI_API_SQLITE_PATH", str(tmp_path / "logos.sqlite"))
    image = b"\x89PNG\r\n\x1a\n" + b"test-image-data"
    digest = save_organizer_logo(42, base64.b64encode(image).decode("ascii"))
    assert get_organizer_logo(digest) == ("image/png", image)
    assert get_organizer_logo("invalid") is None
    with pytest.raises(ValueError):
        save_organizer_logo(42, base64.b64encode(b"<svg/>").decode("ascii"))
