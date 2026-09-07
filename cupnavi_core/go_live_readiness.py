"""Pure go-live readiness decisions for organisers before a real cup starts."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


def _int(stats: Mapping[str, Any], key: str) -> int:
    try:
        return int(stats.get(key, 0) or 0)
    except (TypeError, ValueError):
        return 0


@dataclass(frozen=True)
class GoLiveReadinessItem:
    key: str
    label: str
    state: str  # ok | warning | blocker
    detail: str
    action_page: str | None = None


@dataclass(frozen=True)
class GoLiveReadiness:
    items: tuple[GoLiveReadinessItem, ...]

    @property
    def blockers(self) -> tuple[GoLiveReadinessItem, ...]:
        return tuple(item for item in self.items if item.state == "blocker")

    @property
    def warnings(self) -> tuple[GoLiveReadinessItem, ...]:
        return tuple(item for item in self.items if item.state == "warning")

    @property
    def ready(self) -> bool:
        return not self.blockers

    @property
    def ok_count(self) -> int:
        return sum(1 for item in self.items if item.state == "ok")


def build_go_live_readiness(
    *,
    cloud_database_enabled: bool,
    database_config_partial: bool = False,
    admin_access_configured: bool = True,
    production_environment: bool = True,
    schema_version: int,
    required_schema_version: int,
    missing_tables: list[str] | tuple[str, ...],
    published: bool,
    schedule_dirty: bool,
    schedule_errors: list[str] | tuple[str, ...],
    stats: Mapping[str, Any],
) -> GoLiveReadiness:
    """Build a conservative, actionable pre-cup readiness result.

    Only conditions that can prevent safe live operation are blockers. Optional
    enhancements, such as full player rosters, remain warnings so CupNavi does
    not invent requirements that the organiser may not use.
    """
    items: list[GoLiveReadinessItem] = []

    if production_environment:
        items.append(GoLiveReadinessItem(
            "environment", "Cupmiljö", "ok",
            "Cupen är markerad som Riktig cup.",
        ))
    else:
        items.append(GoLiveReadinessItem(
            "environment", "Cupmiljö", "blocker",
            "Cupen är fortfarande Testmiljö. Skarp start får inte godkännas förrän rätt produktionscup används.",
            "Cupinställningar",
        ))

    if database_config_partial:
        items.append(GoLiveReadinessItem(
            "database", "Produktionsdatabas", "blocker",
            "Turso är bara delvis konfigurerat. Både TURSO_DATABASE_URL och TURSO_AUTH_TOKEN måste finnas.",
            "Cupinställningar",
        ))
    elif cloud_database_enabled:
        items.append(GoLiveReadinessItem(
            "database", "Produktionsdatabas", "ok",
            "Turso är aktivt. Cupdata delas mellan enheter och sessioner.",
        ))
    else:
        items.append(GoLiveReadinessItem(
            "database", "Produktionsdatabas", "blocker",
            "CupNavi kör mot lokal databas. Skarpt test ska köras mot Turso.",
            "Cupinställningar",
        ))

    if admin_access_configured:
        items.append(GoLiveReadinessItem(
            "admin_access", "Adminskydd", "ok",
            "ADMIN_PASSWORD är konfigurerat för webbdrift.",
        ))
    else:
        items.append(GoLiveReadinessItem(
            "admin_access", "Adminskydd", "blocker",
            "ADMIN_PASSWORD saknas. Administration får inte gå skarpt utan ett separat adminlösenord.",
            "Cupinställningar",
        ))

    if int(schema_version) >= int(required_schema_version) and not missing_tables:
        items.append(GoLiveReadinessItem(
            "schema", "Databasschema", "ok",
            f"Schema v{schema_version} är kompatibelt och kritiska tabeller finns.",
        ))
    else:
        detail_parts: list[str] = []
        if int(schema_version) < int(required_schema_version):
            detail_parts.append(f"schema v{schema_version}, kräver minst v{required_schema_version}")
        if missing_tables:
            detail_parts.append("saknade tabeller: " + ", ".join(missing_tables))
        items.append(GoLiveReadinessItem(
            "schema", "Databasschema", "blocker",
            "Databasen är inte redo: " + "; ".join(detail_parts) + ".",
            "Cupinställningar",
        ))

    reporter_codes = _int(stats, "reporter_codes")
    if reporter_codes > 0:
        items.append(GoLiveReadinessItem(
            "reporter_code", "Matchrapportörskod", "ok",
            "En aktiv kod finns för matchrapportering.",
        ))
    else:
        items.append(GoLiveReadinessItem(
            "reporter_code", "Matchrapportörskod", "blocker",
            "Skapa en kod innan rapportörer ska arbeta från mobil.",
            "Domare",
        ))

    teams = _int(stats, "teams")
    if teams >= 2:
        items.append(GoLiveReadinessItem(
            "teams", "Lag", "ok", f"{teams} lag finns i cupen.", "Lag",
        ))
    else:
        items.append(GoLiveReadinessItem(
            "teams", "Lag", "blocker",
            "Minst två lag behövs för att kunna genomföra och rapportera en match.",
            "Lag",
        ))

    matches = _int(stats, "matches")
    unscheduled = _int(stats, "unscheduled_matches")
    unpublished_matches = _int(stats, "unpublished_matches")
    schedule_problem = bool(schedule_dirty or schedule_errors or matches <= 0 or unscheduled > 0)
    if schedule_problem:
        reasons: list[str] = []
        if matches <= 0:
            reasons.append("inga matcher finns")
        if schedule_dirty:
            reasons.append("schemat är inaktuellt")
        if schedule_errors:
            reasons.append(f"{len(schedule_errors)} kritiska schemafel")
        if unscheduled:
            reasons.append(f"{unscheduled} matcher saknar tid eller plan")
        items.append(GoLiveReadinessItem(
            "schedule", "Spelschema", "blocker",
            "Åtgärda innan start: " + ", ".join(reasons) + ".",
            "Schema",
        ))
    else:
        items.append(GoLiveReadinessItem(
            "schedule", "Spelschema", "ok",
            f"{matches} matcher har tid och plan och schemat är aktuellt.",
            "Schema",
        ))

    public_ready = bool(published and matches > 0 and unpublished_matches == 0)
    if public_ready:
        items.append(GoLiveReadinessItem(
            "publication", "Publikvy", "ok",
            "Cupen och samtliga schemalagda matcher är publicerade.",
        ))
    else:
        reasons: list[str] = []
        if not published:
            reasons.append("cupen är inte publicerad")
        if unpublished_matches:
            reasons.append(f"{unpublished_matches} matcher är inte publicerade")
        items.append(GoLiveReadinessItem(
            "publication", "Publikvy", "blocker",
            "Publiken får inte ett komplett liveflöde: " + ", ".join(reasons or ["publicering saknas"]) + ".",
            "Kontroller",
        ))

    players = _int(stats, "players")
    teams_without_players = _int(stats, "teams_without_players")
    if players > 0 and teams_without_players == 0:
        items.append(GoLiveReadinessItem(
            "rosters", "Spelartrupper", "ok",
            f"{players} spelare är registrerade och alla lag har minst en spelare.",
            "Lag",
        ))
    elif players > 0:
        items.append(GoLiveReadinessItem(
            "rosters", "Spelartrupper", "warning",
            f"{teams_without_players} lag saknar spelare. Resultat fungerar, men målskytt/assist blir ofullständigt.",
            "Lag",
        ))
    else:
        items.append(GoLiveReadinessItem(
            "rosters", "Spelartrupper", "warning",
            "Inga spelare är registrerade. Resultat fungerar, men målskytt och assist kan inte rapporteras.",
            "Lag",
        ))

    testable_matches = _int(stats, "testable_matches")
    if testable_matches > 0:
        items.append(GoLiveReadinessItem(
            "test_match", "Genrep kan köras", "ok",
            f"{testable_matches} gruppspelsmatch(er) är schemalagda och kan användas för ett skarpt mobiltest.",
            "Matcher och resultat",
        ))
    else:
        items.append(GoLiveReadinessItem(
            "test_match", "Genrep kan köras", "blocker",
            "Det finns ingen schemalagd gruppspelsmatch att använda för live-testet.",
            "Schema",
        ))

    return GoLiveReadiness(tuple(items))


def readiness_icon(state: str) -> str:
    return {"ok": "✅", "warning": "⚠️", "blocker": "⛔"}.get(state, "•")
