"""Authenticated tournament member, role and activity endpoints."""
from __future__ import annotations

from fastapi import Header, HTTPException
from pydantic import BaseModel
from .admin_auth import issue_session
from .admin_repository import organizer_account

from .access_repository import (
    add_tournament_member,
    change_password,
    remove_tournament_member,
    tournament_activity,
    tournament_members,
    tournament_role,
    update_tournament_member_role,
)


class MemberWrite(BaseModel):
    email: str
    display_name: str | None = None
    role: str = "admin"


class MemberRoleWrite(BaseModel):
    role: str


class PasswordWrite(BaseModel):
    current_password: str
    new_password: str


def register_access_routes(app, admin_identity):
    @app.get("/api/admin/cups/{tournament_id}/members")
    def get_members(tournament_id: int, authorization: str | None = Header(default=None)):
        account = admin_identity(authorization)
        members = tournament_members(int(account["id"]), tournament_id)
        if members is None:
            raise HTTPException(status_code=404, detail="Cup not found or access denied")
        return {
            "members": members,
            "current_role": tournament_role(int(account["id"]), tournament_id),
            "can_manage": tournament_role(int(account["id"]), tournament_id) in {"owner", "platform_owner"},
        }

    @app.post("/api/admin/cups/{tournament_id}/members", status_code=201)
    def post_member(tournament_id: int, payload: MemberWrite, authorization: str | None = Header(default=None)):
        account = admin_identity(authorization)
        try:
            dump = getattr(payload, "model_dump", None)
            values = dump() if callable(dump) else payload.dict()
            result = add_tournament_member(account, tournament_id, values)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return result

    @app.put("/api/admin/cups/{tournament_id}/members/{member_id}")
    def put_member_role(tournament_id: int, member_id: int, payload: MemberRoleWrite, authorization: str | None = Header(default=None)):
        account = admin_identity(authorization)
        try:
            member = update_tournament_member_role(account, tournament_id, member_id, payload.role)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        if not member:
            raise HTTPException(status_code=404, detail="Administratören finns inte i cupen")
        return member

    @app.delete("/api/admin/cups/{tournament_id}/members/{member_id}")
    def delete_member(tournament_id: int, member_id: int, authorization: str | None = Header(default=None)):
        account = admin_identity(authorization)
        try:
            removed = remove_tournament_member(account, tournament_id, member_id)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        if not removed:
            raise HTTPException(status_code=404, detail="Administratören finns inte i cupen")
        return {"removed": True}

    @app.get("/api/admin/cups/{tournament_id}/activity")
    def get_activity(tournament_id: int, authorization: str | None = Header(default=None)):
        account = admin_identity(authorization)
        rows = tournament_activity(int(account["id"]), tournament_id)
        if rows is None:
            raise HTTPException(status_code=404, detail="Cup not found or access denied")
        return {"activity": rows}

    @app.put("/api/admin/account/password")
    def put_password(payload: PasswordWrite, authorization: str | None = Header(default=None)):
        account = admin_identity(authorization)
        try:
            change_password(int(account["id"]), payload.current_password, payload.new_password)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        refreshed = organizer_account(int(account["id"]))
        return {"changed": True, "token": issue_session(refreshed)}
