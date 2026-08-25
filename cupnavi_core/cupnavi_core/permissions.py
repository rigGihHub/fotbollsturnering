"""Role/permission model for future multi-tenant CupNavi accounts."""
from __future__ import annotations

ROLE_PERMISSIONS = {
    "admin": frozenset({"tournament.manage", "participant.manage", "schedule.manage", "match.report", "official.manage", "publication.manage"}),
    "competition_manager": frozenset({"participant.manage", "schedule.manage", "match.report", "official.manage", "publication.manage"}),
    "match_reporter": frozenset({"match.report"}),
    "official": frozenset({"match.view_assigned", "match.acknowledge"}),
    "participant_manager": frozenset({"participant.self_manage", "participant.check_in", "roster.manage", "match_roster.manage"}),
    "viewer": frozenset({"tournament.view_public"}),
}


def permissions_for(role: str | None) -> frozenset[str]:
    return ROLE_PERMISSIONS.get(str(role or "viewer"), ROLE_PERMISSIONS["viewer"])


def can(role: str | None, permission: str) -> bool:
    return permission in permissions_for(role)
