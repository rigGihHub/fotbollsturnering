"""Sponsor and offer endpoints shared by the current admin and public cup views."""
from __future__ import annotations

import base64
import re
from urllib.parse import urlparse

from fastapi import Header, HTTPException
from pydantic import BaseModel

from .admin_repository import admin_cupinfo
from .repository import all_rows, connect, one, public_tournament


class PartnerWrite(BaseModel):
    name: str = ""
    level: str | None = None
    description: str | None = None
    website_url: str | None = None
    logo_data_uri: str | None = None
    active: bool = True
    sort_order: int = 0
    expected: dict | None = None


class OfferWrite(BaseModel):
    title: str = ""
    business_name: str | None = None
    description: str | None = None
    discount_code: str | None = None
    valid_until: str | None = None
    url: str | None = None
    active: bool = True
    sort_order: int = 0
    expected: dict | None = None


def _ensure_tables():
    with connect() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS sponsors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
            name TEXT NOT NULL, level TEXT, description TEXT, website_url TEXT,
            logo_data_uri TEXT, active INTEGER NOT NULL DEFAULT 1,
            sort_order INTEGER NOT NULL DEFAULT 0
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS offers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
            title TEXT NOT NULL, business_name TEXT, description TEXT,
            discount_code TEXT, valid_until TEXT, url TEXT,
            active INTEGER NOT NULL DEFAULT 1, sort_order INTEGER NOT NULL DEFAULT 0
        )""")
        commit = getattr(con, "commit", None)
        if callable(commit):
            commit()


def _text(value, limit, required=False):
    result = str(value or "").strip()
    if required and not result:
        raise HTTPException(status_code=422, detail="Namn eller rubrik måste anges")
    if len(result) > limit:
        raise HTTPException(status_code=422, detail=f"Texten får vara högst {limit} tecken")
    return result or None


def _url(value):
    text = _text(value, 500)
    if not text:
        return None
    if re.match(r"^[a-z][a-z0-9+.-]*:", text, re.I) and not re.match(r"^https?://", text, re.I):
        raise HTTPException(status_code=422, detail="Ange en giltig webbadress")
    if not re.match(r"^https?://", text, re.I):
        text = "https://" + text
    parsed = urlparse(text)
    if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password or " " in text:
        raise HTTPException(status_code=422, detail="Ange en giltig webbadress")
    return text


def _logo(value):
    if not value:
        return None
    match = re.fullmatch(r"data:image/(png|jpeg|webp);base64,([A-Za-z0-9+/=]+)", value)
    if not match:
        raise HTTPException(status_code=422, detail="Logotypen måste vara PNG, JPG eller WEBP")
    try:
        image = base64.b64decode(match.group(2), validate=True)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Logotypen kunde inte läsas") from exc
    signatures = {
        "png": image.startswith(b"\x89PNG\r\n\x1a\n"),
        "jpeg": image.startswith(b"\xff\xd8\xff"),
        "webp": image.startswith(b"RIFF") and image[8:12] == b"WEBP",
    }
    if not image or len(image) > 1_500_000 or not signatures[match.group(1)]:
        raise HTTPException(status_code=422, detail="Logotypen är ogiltig eller över 1,5 MB")
    return value


def _values(kind, payload):
    if not 0 <= payload.sort_order <= 999:
        raise HTTPException(status_code=422, detail="Visningsordning måste vara 0–999")
    if kind == "sponsors":
        return {
            "name": _text(payload.name, 150, required=True),
            "level": _text(payload.level, 80),
            "description": _text(payload.description, 1000),
            "website_url": _url(payload.website_url),
            "logo_data_uri": _logo(payload.logo_data_uri),
            "active": int(payload.active),
            "sort_order": payload.sort_order,
        }
    return {
        "title": _text(payload.title, 150, required=True),
        "business_name": _text(payload.business_name, 150),
        "description": _text(payload.description, 1500),
        "discount_code": _text(payload.discount_code, 100),
        "valid_until": _text(payload.valid_until, 80),
        "url": _url(payload.url),
        "active": int(payload.active),
        "sort_order": payload.sort_order,
    }


def _access(account_id, cup_id):
    if not admin_cupinfo(account_id, cup_id):
        raise HTTPException(status_code=404, detail="Cup saknas eller åtkomst nekas")


def _list(cup_id, public=False):
    _ensure_tables()
    condition = " AND active=1" if public else ""
    return {
        "sponsors": all_rows(
            f"SELECT * FROM sponsors WHERE tournament_id=?{condition} ORDER BY sort_order,id", (cup_id,)
        ),
        "offers": all_rows(
            f"SELECT * FROM offers WHERE tournament_id=?{condition} ORDER BY sort_order,id", (cup_id,)
        ),
    }


def _write(kind, cup_id, payload, item_id=None):
    values = _values(kind, payload)
    if item_id is not None:
        current = one(f"SELECT * FROM {kind} WHERE id=? AND tournament_id=?", (item_id, cup_id))
        if not current:
            raise HTTPException(status_code=404, detail="Posten saknas")
        # A second open admin tab must not silently overwrite a newer edit.
        if not payload.expected or any(current.get(key) != payload.expected.get(key) for key in values):
            raise HTTPException(status_code=409, detail="Posten har ändrats. Ladda om och försök igen.")
        columns = list(values)
        with connect() as con:
            cursor = con.execute(
                f"UPDATE {kind} SET " + ",".join(f"{key}=?" for key in columns)
                + " WHERE id=? AND tournament_id=? AND "
                + " AND ".join(f"{key} IS ?" for key in columns),
                (*[values[key] for key in columns], item_id, cup_id, *[current[key] for key in columns]),
            )
            changed = cursor.rowcount
            commit = getattr(con, "commit", None)
            if callable(commit):
                commit()
        if changed == 0:
            raise HTTPException(status_code=409, detail="Posten har ändrats. Ladda om och försök igen.")
        return one(f"SELECT * FROM {kind} WHERE id=? AND tournament_id=?", (item_id, cup_id))
    columns = list(values)
    with connect() as con:
        con.execute(
            f"INSERT INTO {kind} (tournament_id," + ",".join(columns) + ") VALUES (?"
            + ",?" * len(columns) + ")",
            (cup_id, *[values[key] for key in columns]),
        )
        cursor = con.execute("SELECT last_insert_rowid()")
        new_id = cursor.fetchone()[0]
        commit = getattr(con, "commit", None)
        if callable(commit):
            commit()
    return one(f"SELECT * FROM {kind} WHERE id=? AND tournament_id=?", (new_id, cup_id))


def register_partner_routes(app, admin_identity):
    @app.get("/api/public/cups/{public_key}/partners")
    def public_partners(public_key: str):
        tournament = public_tournament(public_key)
        if not tournament:
            raise HTTPException(status_code=404, detail="Cup saknas eller är inte publicerad")
        return _list(int(tournament["id"]), public=True)

    @app.get("/api/admin/cups/{cup_id}/partners")
    def admin_partners(cup_id: int, authorization: str | None = Header(default=None)):
        account = admin_identity(authorization)
        _access(int(account["id"]), cup_id)
        return _list(cup_id)

    @app.post("/api/admin/cups/{cup_id}/sponsors", status_code=201)
    def create_sponsor(cup_id: int, payload: PartnerWrite, authorization: str | None = Header(default=None)):
        account = admin_identity(authorization)
        _access(int(account["id"]), cup_id)
        _ensure_tables()
        return _write("sponsors", cup_id, payload)

    @app.put("/api/admin/cups/{cup_id}/sponsors/{item_id}")
    def update_sponsor(cup_id: int, item_id: int, payload: PartnerWrite, authorization: str | None = Header(default=None)):
        account = admin_identity(authorization)
        _access(int(account["id"]), cup_id)
        return _write("sponsors", cup_id, payload, item_id)

    @app.post("/api/admin/cups/{cup_id}/offers", status_code=201)
    def create_offer(cup_id: int, payload: OfferWrite, authorization: str | None = Header(default=None)):
        account = admin_identity(authorization)
        _access(int(account["id"]), cup_id)
        _ensure_tables()
        return _write("offers", cup_id, payload)

    @app.put("/api/admin/cups/{cup_id}/offers/{item_id}")
    def update_offer(cup_id: int, item_id: int, payload: OfferWrite, authorization: str | None = Header(default=None)):
        account = admin_identity(authorization)
        _access(int(account["id"]), cup_id)
        return _write("offers", cup_id, payload, item_id)

    def remove(kind, cup_id, item_id, authorization):
        account = admin_identity(authorization)
        _access(int(account["id"]), cup_id)
        with connect() as con:
            cursor = con.execute(f"DELETE FROM {kind} WHERE id=? AND tournament_id=?", (item_id, cup_id))
            changed = cursor.rowcount
            commit = getattr(con, "commit", None)
            if callable(commit):
                commit()
        if changed == 0:
            raise HTTPException(status_code=404, detail="Posten saknas")
        return {"deleted": True}

    @app.delete("/api/admin/cups/{cup_id}/sponsors/{item_id}")
    def delete_sponsor(cup_id: int, item_id: int, authorization: str | None = Header(default=None)):
        return remove("sponsors", cup_id, item_id, authorization)

    @app.delete("/api/admin/cups/{cup_id}/offers/{item_id}")
    def delete_offer(cup_id: int, item_id: int, authorization: str | None = Header(default=None)):
        return remove("offers", cup_id, item_id, authorization)
