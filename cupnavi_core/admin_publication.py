"""Pure publication/readiness decisions for the CupNavi admin UI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence


_ADVISORY_WARNING_TERMS = ("färgkrock", "tröjfärg", "färglikhet", "extraställ")


def is_advisory_schedule_warning(message: str | None) -> bool:
    """Return True for kit-colour warnings that should never block publishing."""
    lowered = (message or "").lower()
    return any(term in lowered for term in _ADVISORY_WARNING_TERMS)


def split_schedule_warnings(warnings: Iterable[str]) -> tuple[list[str], list[str]]:
    """Split schedule warnings into blocking and advisory groups, preserving order."""
    blocking: list[str] = []
    advisory: list[str] = []
    for warning in warnings:
        (advisory if is_advisory_schedule_warning(warning) else blocking).append(warning)
    return blocking, advisory


def build_publish_blockers(
    *,
    playoff_model_confirmed: bool,
    scheduled_matches: int,
    schedule_dirty: bool,
    schedule_errors: Sequence[str],
    blocking_warnings: Sequence[str] = (),
    warnings_approved: bool = False,
) -> list[str]:
    """Return only conditions that make publication unsafe.

    Schedule warnings are intentionally not blockers. validate_schedule already
    separates hard errors from warnings; forcing an extra acknowledgement made
    ordinary warnings behave like errors and created two competing severity
    systems in the UI. The legacy warning arguments remain for API compatibility.
    """
    blockers: list[str] = []
    if not playoff_model_confirmed:
        blockers.append("Slutspelsmodell och cupregler måste sparas på Översikt.")
    if not int(scheduled_matches or 0):
        blockers.append("Spelschema saknas. Generera schemat under Schema.")
    if schedule_dirty and int(scheduled_matches or 0):
        blockers.append("Schemat är inaktuellt eftersom förutsättningarna har ändrats. Regenerera schemat.")
    if schedule_errors:
        blockers.append(f"{len(schedule_errors)} blockerande schemafel måste åtgärdas.")
    return blockers


@dataclass(frozen=True)
class PublicationQualitySummary:
    critical: tuple[str, ...]
    warnings: tuple[str, ...]
    improvements: tuple[str, ...]
    can_publish: bool


def build_publication_quality_summary(
    *,
    playoff_model_confirmed: bool,
    scheduled_matches: int,
    schedule_dirty: bool,
    schedule_errors: Sequence[str],
    schedule_warnings: Sequence[str],
) -> PublicationQualitySummary:
    """Create one severity model shared by publication and Kontroller."""
    critical = build_publish_blockers(
        playoff_model_confirmed=playoff_model_confirmed,
        scheduled_matches=scheduled_matches,
        schedule_dirty=schedule_dirty,
        schedule_errors=schedule_errors,
    )
    warning_items, improvement_items = split_schedule_warnings(schedule_warnings)
    return PublicationQualitySummary(
        critical=tuple(critical),
        warnings=tuple(warning_items),
        improvements=tuple(improvement_items),
        can_publish=not bool(critical),
    )


def publication_action_label(*, published_once: bool) -> str:
    return "Uppdatera" if published_once else "Publicera"


@dataclass(frozen=True)
class CompletionState:
    total: int
    played: int
    can_complete: bool


def build_completion_state(*, total: int, played: int, lifecycle: str) -> CompletionState:
    total_i = max(0, int(total or 0))
    played_i = max(0, int(played or 0))
    return CompletionState(
        total=total_i,
        played=played_i,
        can_complete=total_i > 0 and played_i == total_i and lifecycle in ("published", "live"),
    )
