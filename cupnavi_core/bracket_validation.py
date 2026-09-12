"""Validate playoff bracket source graphs before a cup is published.

The validator is intentionally storage-agnostic. It inspects symbolic participant
sources and returns organizer-facing structural errors without resolving live
scores or mutating bracket provenance.
"""
from __future__ import annotations

from dataclasses import dataclass

from .participant_sources import parse_participant_source


@dataclass(frozen=True)
class BracketIssue:
    code: str
    message: str
    match_id: int | None = None
    source: str = ""

    def as_dict(self) -> dict:
        return {
            "code": self.code,
            "message": self.message,
            "match_id": self.match_id,
            "source": self.source,
        }


def validate_bracket_sources(matches: list[dict], teams: list[dict], groups: list[dict]) -> dict:
    """Return structural bracket issues and a compact readiness summary.

    Rules:
    - playoff slots must not be empty;
    - direct team/group references must target existing tournament entities;
    - winner/loser references must target another existing match;
    - a match may not depend on itself;
    - winner/loser dependencies must be acyclic, including multi-step cycles;
    - group placement must be positive.
    """
    match_by_id = {int(row["id"]): row for row in matches if row.get("id") is not None}
    team_ids = {int(row["id"]) for row in teams if row.get("id") is not None}
    group_ids = {int(row["id"]) for row in groups if row.get("id") is not None}
    playoff_matches = [row for row in matches if row.get("bracket_id") is not None]
    issues: list[BracketIssue] = []
    edges: dict[int, set[int]] = {int(row["id"]): set() for row in playoff_matches if row.get("id") is not None}

    for row in playoff_matches:
        match_id = int(row["id"])
        for side, value in (("hemmaplatsen", row.get("home_source")), ("bortaplatsen", row.get("away_source"))):
            parsed = parse_participant_source(value)
            raw = parsed.raw
            if parsed.kind == "empty":
                issues.append(BracketIssue("empty_slot", f"Match {match_id}: {side} saknar deltagarkälla.", match_id, raw))
                continue
            if parsed.kind == "team":
                if int(parsed.source_id) not in team_ids:
                    issues.append(BracketIssue("team_missing", f"Match {match_id}: {side} hänvisar till ett lag som inte finns.", match_id, raw))
                continue
            if parsed.kind == "group":
                if int(parsed.source_id) not in group_ids:
                    issues.append(BracketIssue("group_missing", f"Match {match_id}: {side} hänvisar till en grupp som inte finns.", match_id, raw))
                if int(parsed.placement or 0) <= 0:
                    issues.append(BracketIssue("group_placement_invalid", f"Match {match_id}: {side} har en ogiltig gruppplacering.", match_id, raw))
                continue
            if parsed.kind in {"winner", "loser"}:
                source_id = int(parsed.source_id)
                if source_id == match_id:
                    issues.append(BracketIssue("self_dependency", f"Match {match_id} kan inte bero på sitt eget resultat.", match_id, raw))
                    continue
                if source_id not in match_by_id:
                    issues.append(BracketIssue("source_match_missing", f"Match {match_id}: {side} hänvisar till match {source_id}, som inte finns.", match_id, raw))
                    continue
                edges.setdefault(source_id, set()).add(match_id)
                continue
            if parsed.kind == "legacy":
                issues.append(BracketIssue("legacy_source", f"Match {match_id}: {side} använder en äldre fri text-källa som inte kan valideras säkert.", match_id, raw))
                continue
            issues.append(BracketIssue("unsupported_source", f"Match {match_id}: {side} har en deltagarkälla som CupNavi inte kan tolka.", match_id, raw))

    visiting: set[int] = set()
    visited: set[int] = set()
    cycle_nodes: set[int] = set()

    def visit(node: int, trail: tuple[int, ...] = ()) -> None:
        if node in visited:
            return
        if node in visiting:
            if node in trail:
                cycle_nodes.update(trail[trail.index(node):])
            else:
                cycle_nodes.add(node)
            return
        visiting.add(node)
        for child in edges.get(node, ()):
            visit(child, trail + (node,))
        visiting.discard(node)
        visited.add(node)

    for node in tuple(edges):
        visit(node)

    for node in sorted(cycle_nodes):
        issues.append(BracketIssue("dependency_cycle", f"Match {node} ingår i en cirkulär slutspelsberoendekedja.", node))

    unique: list[BracketIssue] = []
    seen = set()
    for issue in issues:
        key = (issue.code, issue.match_id, issue.source)
        if key not in seen:
            seen.add(key)
            unique.append(issue)

    return {
        "ready": not unique,
        "issue_count": len(unique),
        "issues": [issue.as_dict() for issue in unique],
        "playoff_match_count": len(playoff_matches),
    }
