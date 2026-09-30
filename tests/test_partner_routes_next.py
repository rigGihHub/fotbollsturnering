"""The restored Next.js partner flow must keep cup and publication boundaries."""
import base64
import sqlite3

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from cupnavi_api import partner_routes


def test_partner_crud_and_public_visibility_are_cup_scoped(monkeypatch, tmp_path):
    path = tmp_path / "partners.db"
    with sqlite3.connect(path) as con:
        con.execute("CREATE TABLE tournaments (id INTEGER PRIMARY KEY, public_slug TEXT, is_published INTEGER)")
        con.executemany(
            "INSERT INTO tournaments VALUES (?,?,?)",
            [(1, "cup-one", 1), (2, "cup-two", 1)],
        )
    monkeypatch.setenv("CUPNAVI_API_SQLITE_PATH", str(path))
    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
    monkeypatch.delenv("TURSO_AUTH_TOKEN", raising=False)
    monkeypatch.setattr(
        partner_routes, "admin_cupinfo",
        lambda account_id, cup_id: {"id": cup_id} if account_id == cup_id else None,
    )
    monkeypatch.setattr(
        partner_routes, "public_tournament",
        lambda slug: {"id": 1} if slug == "cup-one" else ({"id": 2} if slug == "cup-two" else None),
    )
    app = FastAPI()

    def auth(header):
        if header != "Bearer owner":
            raise HTTPException(401)
        return {"id": 1}

    partner_routes.register_partner_routes(app, auth)
    client = TestClient(app)
    headers = {"Authorization": "Bearer owner"}
    sponsor = client.post("/api/admin/cups/1/sponsors", headers=headers, json={
        "name": "Lokala Banken", "website_url": "banken.se", "active": False,
    })
    assert sponsor.status_code == 201
    item = sponsor.json()
    assert item["website_url"] == "https://banken.se"
    assert client.get("/api/public/cups/cup-one/partners").json()["sponsors"] == []
    assert client.get("/api/admin/cups/2/partners", headers=headers).status_code == 404
    assert client.get("/api/admin/cups/1/partners").status_code == 401
    assert client.get("/api/public/cups/cup-two/partners").json()["sponsors"] == []

    logo = "data:image/png;base64," + base64.b64encode(
        b"\x89PNG\r\n\x1a\n" + b"test image content"
    ).decode()
    updated = client.put(f"/api/admin/cups/1/sponsors/{item['id']}", headers=headers, json={
        **item, "active": True, "logo_data_uri": logo, "expected": item,
    })
    assert updated.status_code == 200
    assert client.get("/api/public/cups/cup-one/partners").json()["sponsors"][0]["logo_data_uri"] == logo
    assert client.put(f"/api/admin/cups/1/sponsors/{item['id']}", headers=headers, json={
        **item, "name": "Old tab overwrites", "expected": item,
    }).status_code == 409
    assert client.post("/api/admin/cups/1/sponsors", headers=headers, json={
        "name": "Unsafe", "website_url": "javascript:alert(1)",
    }).status_code == 422

    offer = client.post("/api/admin/cups/1/offers", headers=headers, json={
        "title": "20 % rabatt", "business_name": "Lokala Banken",
        "discount_code": "CUP20", "active": True,
    })
    assert offer.status_code == 201
    assert client.get("/api/public/cups/cup-one/partners").json()["offers"][0]["discount_code"] == "CUP20"
    assert client.delete(f"/api/admin/cups/2/offers/{offer.json()['id']}", headers=headers).status_code == 404
    assert client.delete(f"/api/admin/cups/1/offers/{offer.json()['id']}", headers=headers).json()["deleted"]
    assert client.get("/api/public/cups/cup-one/partners").json()["offers"] == []
