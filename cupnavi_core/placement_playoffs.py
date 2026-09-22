"""Explicit draw-based playoff groups, derived from preserved participant sources."""
from collections import defaultdict
from itertools import combinations

from .participant_sources import parse_participant_source
from .public_competition import calculate_group_table

DRAW_RULE = "Oavgjort tillåtet – tabell avgör"


def placement_blocks(matches):
    """Recognize complete single round robins, never infer from 'brons' alone.

    At least three distinct participants must meet exactly once in each named
    group. Winner/loser dependencies and repeated or missing pairs fail closed.
    """
    buckets = defaultdict(list)
    for match in matches:
        if match.get("bracket_id") is not None:
            buckets[(match["bracket_id"], str(match.get("stage") or "").strip())].append(match)
    blocks = []
    for (bracket_id, name), rows in buckets.items():
        sources = sorted({str(row.get(side) or "") for row in rows for side in ("home_source", "away_source")})
        parsed = [parse_participant_source(source) for source in sources]
        if not name or len(sources) < 3 or any(p.kind not in {"group", "team"} for p in parsed):
            continue
        ranks = {p.placement for p in parsed if p.kind == "group"}
        if len(ranks) > 1:
            continue
        pairs = [frozenset((row.get("home_source"), row.get("away_source"))) for row in rows]
        if len(pairs) != len(set(pairs)) or set(pairs) != {frozenset(pair) for pair in combinations(sources, 2)}:
            continue
        blocks.append({"bracket_id": bracket_id, "name": name, "sources": sources,
                       "placement": next(iter(ranks)) if len(ranks) == 1 and all(p.kind == "group" for p in parsed) else None,
                       "matches": rows})
    return sorted(blocks, key=lambda b: (b["placement"] or 999, b["name"]))


def all_placement_blocks(matches):
    blocks = placement_blocks(matches)
    bracket_matches = [row for row in matches if row.get("bracket_id") is not None]
    if not bracket_matches or sum(len(b["matches"]) for b in blocks) != len(bracket_matches):
        return []
    # A participant cannot belong to two final groups. Nor may any other match
    # depend on the winner/loser of a game that is allowed to finish as a draw.
    sources = [source for b in blocks for source in b["sources"]]
    if len(sources) != len(set(sources)):
        return []
    ids = {row["id"] for row in bracket_matches}
    for row in matches:
        for side in ("home_source", "away_source"):
            p = parse_participant_source(row.get(side))
            if p.kind in {"winner", "loser"} and p.source_id in ids:
                return []
    return blocks


def draw_match_ids(tournament, matches):
    if (tournament or {}).get("playoff_tie_rule") != DRAW_RULE:
        return set()
    return {m["id"] for b in all_placement_blocks(matches) for m in b["matches"]}


def source_label(source, group_names):
    p = parse_participant_source(source)
    if p.kind == "group":
        suffix = "a" if p.placement in {1, 2} else "e"
        return f"{p.placement}:{suffix} i grupp {group_names.get(p.source_id, 'okänd')}"
    if p.kind in {"winner", "loser"}:
        return f"{'Vinnare' if p.kind == 'winner' else 'Förlorare'} match {p.source_id}"
    return str(source or "Ej satt")


def placement_tables(tournament, matches, group_names, resolver):
    if (tournament or {}).get("playoff_tie_rule") != DRAW_RULE:
        return []
    result = []
    for block in all_placement_blocks(matches):
        slots = {source: i for i, source in enumerate(block["sources"], 1)}
        resolved = {source: resolver.resolve(source) for source in slots}
        teams = [{"id": i, "name": resolved[source].team_name or source_label(source, group_names)} for source, i in slots.items()]
        completed = [m for m in block["matches"] if m.get("home_score") is not None and m.get("away_score") is not None
                     and m.get("match_status") not in {"live", "halftime"}]
        games = [{**m, "home_source": f"team:{slots[m['home_source']]}", "away_source": f"team:{slots[m['away_source']]}"} for m in completed]
        rows = calculate_group_table(teams, games, points_win=tournament.get("points_win", 3) or 0,
                                     points_draw=tournament.get("points_draw", 1) or 0, points_loss=tournament.get("points_loss", 0) or 0,
                                     table_tiebreak=tournament.get("table_tiebreak") or "Målskillnad först")
        for row in rows:
            source = block["sources"][row["team_id"] - 1]
            row["source"] = source
            row["resolved_team_id"] = resolved[source].team_id
        complete = len(completed) == len(block["matches"]) and all(p.resolved for p in resolved.values())
        # Alphabetical fallback orders equal rows but must never crown a winner.
        # With head-to-head rules, be conservative if the leaders' total stats tie.
        tied_top = len(rows) > 1 and all(rows[0][k] == rows[1][k] for k in ("P", "MS", "GM"))
        result.append({"name": block["name"], "bracket_id": block["bracket_id"], "placement": block["placement"],
                       "match_ids": [m["id"] for m in block["matches"]], "rows": rows, "complete": complete,
                       "winner": rows[0]["Lag"] if complete and not tied_top else None,
                       "ranking_tied": complete and tied_top})
    return result
