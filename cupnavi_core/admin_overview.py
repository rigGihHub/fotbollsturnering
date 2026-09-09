from __future__ import annotations

import html
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from cupnavi_core.product_foundation import organizer_workflow, workflow_summary
from cupnavi_core.ux2 import attention_items, workflow_progress


def _value(row: Any, key: str, default: Any = None) -> Any:
    if row is None:
        return default
    if isinstance(row, Mapping):
        return row.get(key, default)
    try:
        value = row[key]
    except (KeyError, IndexError, TypeError):
        return default
    return default if value is None else value


def _count(counts: Any, key: str) -> int:
    try:
        return int(_value(counts, key, 0) or 0)
    except (TypeError, ValueError):
        return 0


@dataclass(frozen=True)
class AdminReadiness:
    teams_ready: bool
    groups_ready: bool
    players_ready: bool
    referees_ready: bool
    schedule_ready: bool
    results_ready: bool


@dataclass(frozen=True)
class AdminNextStep:
    title: str
    target: str
    text: str


@dataclass(frozen=True)
class AdminDecisionSummary:
    status: str
    title: str
    text: str
    target: str
    action_label: str
    missing: tuple[tuple[str, str, str], ...]
    publish_ready: bool


def build_admin_decision_summary(
    counts: Any,
    *,
    cupinfo_ready: bool,
    expected_teams: int,
    rules_confirmed: bool,
    schedule_dirty: bool,
    published: bool,
    validation_ready: bool = False,
    validation_errors: Sequence[str] = (),
) -> AdminDecisionSummary:
    """One novice-facing decision model for the admin overview.

    The overview should answer three questions without forcing the organiser to
    interpret counters: What should I do now? What is still missing? Can I
    publish? Validation is deliberately not recomputed here; a known-fresh
    validation snapshot can promote the state to publish-ready, otherwise the
    organiser is sent to the explicit Kontroll step.
    """
    teams_n = _count(counts, "teams_n")
    groups_n = _count(counts, "groups_n")
    unassigned_n = _count(counts, "unassigned_n")
    pitches_n = _count(counts, "pitches_n")
    matches_n = _count(counts, "matches_n")
    scheduled_n = _count(counts, "scheduled_n")
    played_n = _count(counts, "played_n")

    teams_ready = teams_n > 0 and (not int(expected_teams or 0) or teams_n >= int(expected_teams or 0))
    groups_ready = groups_n > 0 and unassigned_n == 0
    schedule_ready = matches_n > 0 and scheduled_n > 0 and not bool(schedule_dirty)

    missing: list[tuple[str, str, str]] = []
    if not cupinfo_ready:
        missing.append(("Cupinfo", "Namn och cupdatum behöver vara klara.", "Cupinställningar"))
    if not teams_ready:
        if expected_teams:
            detail = f"{teams_n}/{int(expected_teams)} lag registrerade."
        else:
            detail = "Lägg till de deltagande lagen."
        missing.append(("Lag", detail, "Lag"))
    if teams_ready and not groups_ready:
        detail = f"{unassigned_n} lag saknar grupp." if unassigned_n else "Skapa grupper och placera lagen."
        missing.append(("Grupper", detail, "Grupper"))
    if not rules_confirmed:
        missing.append(("Regler", "Spara cupens match- och slutspelsregler.", "Regler"))
    if pitches_n <= 0:
        missing.append(("Planer & tider", "Minst en spelplan med tillgängliga tider behövs.", "Planer & tider"))
    if matches_n <= 0 or scheduled_n <= 0:
        missing.append(("Schema", "Spelschema saknas.", "Skapa och publicera schema"))
    elif schedule_dirty:
        missing.append(("Schema", "Förutsättningarna har ändrats. Granska schemat innan publicering.", "Skapa och publicera schema"))

    if published:
        if matches_n and played_n >= matches_n:
            return AdminDecisionSummary(
                "complete", "Alla matcher är rapporterade",
                "Cupen är publicerad och samtliga matcher har resultat. Granska tabell och slutspel.",
                "Tabeller", "Öppna tabeller och slutspel", tuple(missing), False,
            )
        return AdminDecisionSummary(
            "published", "Cupen är publicerad",
            "Publiken ser cupen. Fortsätt med resultat och cupdagsarbete när matcherna spelas.",
            "Matcher och resultat", "Öppna matcher och resultat", tuple(missing), False,
        )

    if missing:
        label, detail, target = missing[0]
        return AdminDecisionSummary(
            "setup", f"Nästa: {label}", detail, target, f"Fortsätt till {label}", tuple(missing), False
        )

    if not validation_ready:
        return AdminDecisionSummary(
            "control", "Grundflödet är klart – gör sista kontrollen",
            "CupNavi behöver köra den fullständiga schemakontrollen innan vi kan säga att cupen är redo att publiceras.",
            "Kontroller", "Kör Kontroll", tuple(), False,
        )

    if validation_errors:
        return AdminDecisionSummary(
            "blocked", "Kontrollen hittade blockerande fel",
            f"{len(validation_errors)} blockerande fel måste åtgärdas före publicering.",
            "Kontroller", "Visa och åtgärda fel", tuple(), False,
        )

    return AdminDecisionSummary(
        "publish", "Cupen är redo att publiceras",
        "Alla obligatoriska steg är klara och den senaste kontrollen har inga blockerande fel.",
        "Kontroller", "Gå till Publicera", tuple(), True,
    )


def rules_ready(rules: Any) -> bool:
    return bool(
        rules
        and int(_value(rules, "halves", 0) or 0) > 0
        and int(_value(rules, "minutes_per_half", 0) or 0) > 0
        and int(_value(rules, "pitch_count", 0) or 0) > 0
        and int(_value(rules, "minimum_team_rest_minutes", 0) or 0) >= 0
    )


def planned_team_total(class_rows: Iterable[Any]) -> int:
    return sum(max(0, int(_value(row, "planned_team_count", 0) or 0)) for row in class_rows)


def build_readiness(counts: Any, *, expected_teams: int, schedule_dirty: bool) -> AdminReadiness:
    teams_n = _count(counts, "teams_n")
    matches_n = _count(counts, "matches_n")
    played_n = _count(counts, "played_n")
    return AdminReadiness(
        teams_ready=teams_n > 0 and (expected_teams == 0 or teams_n == expected_teams),
        groups_ready=_count(counts, "groups_n") > 0,
        players_ready=_count(counts, "players_n") > 0,
        referees_ready=_count(counts, "refs_n") > 0,
        schedule_ready=matches_n > 0 and not schedule_dirty,
        results_ready=matches_n > 0 and played_n == matches_n,
    )


def build_control_status(counts: Any, *, schedule_dirty: bool) -> dict[str, int | bool]:
    delayed = _count(counts, "delayed_n")
    return {
        "upcoming": _count(counts, "upcoming_n"),
        "missing_results": _count(counts, "missing_results_n"),
        "delayed": delayed,
        "schedule_dirty": bool(schedule_dirty),
        "problems": delayed + (1 if schedule_dirty else 0),
    }


def build_progress_and_attention(
    counts: Any,
    *,
    schedule_dirty: bool,
    published: bool,
    checkin_enabled: bool,
    referee_mode: str = "Automatisk",
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    progress = workflow_progress(
        teams_ready=bool(_count(counts, "teams_n")),
        groups_ready=bool(_count(counts, "groups_n")),
        schedule_ready=bool(_count(counts, "matches_n")) and not schedule_dirty,
        referees_ready=bool(_count(counts, "refs_n")),
        published=bool(published),
    )
    missing_refs = 0 if str(referee_mode or "").strip().casefold() == "senare" else _count(counts, "missing_refs_n")
    unchecked = _count(counts, "unchecked_n") if checkin_enabled else 0
    attention = attention_items(
        missing_referees=missing_refs,
        unchecked_teams=unchecked,
        schedule_dirty=bool(schedule_dirty),
        unpublished=not bool(published),
    )
    return progress, attention


def build_organizer_overview(
    counts: Any,
    *,
    class_rows: list[Any],
    sidebar_rules: Any,
    schedule_dirty: bool,
    published: bool,
) -> dict[str, Any]:
    classes_n = len(class_rows)
    planned_total = planned_team_total(class_rows)
    teams_n = _count(counts, "teams_n")
    expected_total = max(planned_total, teams_n)
    steps = organizer_workflow(
        competition_classes=classes_n,
        teams=teams_n,
        expected_teams=expected_total,
        groups=_count(counts, "groups_n"),
        pitches=_count(counts, "pitches_n"),
        rules_ready=rules_ready(sidebar_rules),
        matches=_count(counts, "matches_n"),
        schedule_dirty=bool(schedule_dirty),
        published=bool(published),
    )
    return {
        "classes_n": classes_n,
        "planned_total": planned_total,
        "expected_total": expected_total,
        "steps": steps,
        "summary": workflow_summary(steps),
    }


def class_progress_caption(class_rows: Iterable[Any], team_counts: Mapping[int, int], label_fn) -> str:
    parts: list[str] = []
    for class_row in class_rows:
        class_id = int(_value(class_row, "id", 0) or 0)
        actual = int(team_counts.get(class_id, 0) or 0)
        planned = max(actual, int(_value(class_row, "planned_team_count", 0) or 0))
        label = str(label_fn(class_row))
        parts.append(f"{label}: {actual}/{planned}" if planned else f"{label}: {actual}")
    return "Lag per tävlingsklass · " + " · ".join(parts)


def recommend_next_step(
    readiness: AdminReadiness,
    counts: Any,
    *,
    schedule_dirty: bool,
    published: bool = False,
) -> AdminNextStep:
    """Recommend the next action in the organiser's core journey.

    v401 keeps optional enrichment (rosters/referees) out of the mandatory first
    path. Those tools still exist and can surface as attention items, but a new
    organiser should experience the same promise as setup: Lag → Grupper →
    Schema → Kontroll → Publicera, then move into live result work.
    """
    if not readiness.teams_ready:
        return AdminNextStep("Nästa steg: registrera lag", "Lag", "Lägg in samtliga deltagande lag innan gruppindelning.")
    if not readiness.groups_ready:
        return AdminNextStep("Nästa steg: skapa grupper", "Grupper", "Skapa grupper och placera lagen innan schemat genereras.")
    if _count(counts, "matches_n") == 0:
        return AdminNextStep("Nästa steg: generera schema", "Skapa och publicera schema", "Grunddata är på plats. Generera gruppspel och slutspel.")
    if schedule_dirty:
        return AdminNextStep("Nästa steg: granska schemaändring", "Skapa och publicera schema", "Det finns redan ett schema. CupNavi ändrar ingenting automatiskt. Öppna Schema för att se vad som behöver uppdateras och bekräfta uttryckligen innan befintliga tider eller planer ersätts.")
    if not published:
        return AdminNextStep("Nästa steg: kontrollera och publicera", "Kontroller", "Schemat är klart. Kontrollera kritiska fel och publicera när allt ser rätt ut.")
    if not readiness.results_ready:
        return AdminNextStep("Nästa steg: registrera resultat", "Matcher och resultat", "Cupen är publicerad. Registrera resultaten när matcherna spelas.")
    return AdminNextStep("Nästa steg: granska tävlingsläget", "Tabeller", "Resultaten är registrerade. Granska tabell och slutspel.")


def workflow_step_html(title: str, state: str, meta: str) -> str:
    css_class = "done" if state == "done" else ("warn" if state == "warn" else "todo")
    icon = "✓" if state == "done" else ("⚠" if state == "warn" else "○")
    return (
        f"<div class='cn-step {css_class}'>"
        f"<div class='title'>{icon} {html.escape(title)}</div>"
        f"<div class='meta'>{html.escape(meta)}</div>"
        "</div>"
    )


def build_status_cards_html(counts: Any, *, expected_teams: int, published: bool, schedule_dirty: bool) -> str:
    status = "Publicerad" if published else "Utkast"
    schedule_status = "Schema aktuellt" if not schedule_dirty else "Schema behöver uppdateras"
    planned = expected_teams or "ej satt"
    return f"""
        <div class="cn-dashboard-grid">
          <div class="cn-status-card">
            <div class="cn-label">Lag</div>
            <div class="cn-value">{_count(counts, 'teams_n')}</div>
            <div class="cn-sub">Planerat: {planned}</div>
          </div>
          <div class="cn-status-card">
            <div class="cn-label">Grupper</div>
            <div class="cn-value">{_count(counts, 'groups_n')}</div>
            <div class="cn-sub">Gruppindelning</div>
          </div>
          <div class="cn-status-card">
            <div class="cn-label">Matcher</div>
            <div class="cn-value">{_count(counts, 'matches_n')}</div>
            <div class="cn-sub">Spelade: {_count(counts, 'played_n')}</div>
          </div>
          <div class="cn-status-card">
            <div class="cn-label">Status</div>
            <div class="cn-value">{status}</div>
            <div class="cn-sub">{schedule_status}</div>
          </div>
        </div>
    """


def build_workflow_html(counts: Any, readiness: AdminReadiness) -> str:
    matches_n = _count(counts, "matches_n")
    pieces = [
        workflow_step_html("Lag", "done" if readiness.teams_ready else "todo", f"{_count(counts, 'teams_n')} registrerade"),
        workflow_step_html("Grupper", "done" if readiness.groups_ready else "todo", f"{_count(counts, 'groups_n')} skapade"),
        workflow_step_html("Trupper", "done" if readiness.players_ready else "todo", f"{_count(counts, 'players_n')} spelare"),
        workflow_step_html("Domare", "done" if readiness.referees_ready else "todo", f"{_count(counts, 'refs_n')} registrerade"),
        workflow_step_html(
            "Schema",
            "done" if readiness.schedule_ready else ("warn" if matches_n > 0 else "todo"),
            "Aktuellt" if readiness.schedule_ready else ("Behöver regenereras" if matches_n > 0 else "Ej genererat"),
        ),
        workflow_step_html("Resultat", "done" if readiness.results_ready else "todo", f"{_count(counts, 'played_n')} av {matches_n} matcher"),
    ]
    return "<div class='cn-workflow'>" + "".join(pieces) + "</div>"
