"""Balanced initial pairing generation for Matchcamp."""
from __future__ import annotations

from collections import Counter


def round_robin_rounds(team_ids):
    """Return deterministic round-robin rounds with at most one bye per team/round."""
    teams = [int(x) for x in team_ids]
    if len(teams) < 2:
        return []
    teams = list(dict.fromkeys(teams))
    if len(teams) % 2:
        teams.append(None)

    fixed = teams[0]
    rotating = teams[1:]
    rounds = []
    total_rounds = len(teams) - 1
    for round_index in range(total_rounds):
        lineup = [fixed] + rotating
        pairs = []
        half = len(lineup) // 2
        for i in range(half):
            a = lineup[i]
            b = lineup[-(i + 1)]
            if a is None or b is None:
                continue
            # Alternate orientation to avoid a systematic home/away bias.
            if (round_index + i) % 2:
                a, b = b, a
            pairs.append((int(a), int(b)))
        rounds.append(pairs)
        rotating = [rotating[-1]] + rotating[:-1]
    return rounds


def balanced_matchcamp_pairings(team_ids, matches_per_team):
    """Create a no-repeat, balanced pairing set for a new Matchcamp group.

    For an even number of teams each selected round gives every team one match.
    With an odd number, one team has a bye per round; the rotating circle method
    distributes those byes. Target matches are capped at the number of unique
    opponents, so repeats are never introduced by initial generation.
    """
    teams = [int(x) for x in team_ids]
    teams = list(dict.fromkeys(teams))
    if len(teams) < 2:
        return []
    target = max(1, int(matches_per_team or 1))
    target = min(target, len(teams) - 1)
    rounds = round_robin_rounds(teams)
    return [pair for round_pairs in rounds[:target] for pair in round_pairs]


def complete_matchcamp_pairings(team_ids, existing_pairs, matches_per_team):
    """Safely add missing pairings without deleting existing matches.

    Existing user-created pairings are preserved. New pairs are chosen from
    unique opponents while favoring teams with the fewest current matches.
    """
    teams = list(dict.fromkeys(int(x) for x in team_ids))
    if len(teams) < 2:
        return []
    target = min(max(1, int(matches_per_team or 1)), len(teams) - 1)

    normalized_existing = {
        tuple(sorted((int(a), int(b))))
        for a, b in existing_pairs
        if a is not None and b is not None and int(a) != int(b)
    }
    counts = Counter()
    for a, b in normalized_existing:
        counts[a] += 1
        counts[b] += 1

    preferred = balanced_matchcamp_pairings(teams, target)
    all_candidates = preferred + [
        (a, b)
        for i, a in enumerate(teams)
        for b in teams[i + 1:]
        if tuple(sorted((a, b))) not in {tuple(sorted(x)) for x in preferred}
    ]

    added = []
    used = set(normalized_existing)
    while True:
        under = [tid for tid in teams if counts[tid] < target]
        if len(under) < 2:
            break
        best = None
        best_key = None
        for order, (a, b) in enumerate(all_candidates):
            pair = tuple(sorted((a, b)))
            if pair in used:
                continue
            if counts[a] >= target or counts[b] >= target:
                continue
            key = (max(counts[a], counts[b]), counts[a] + counts[b], order, pair)
            if best_key is None or key < best_key:
                best_key = key
                best = (a, b)
        if best is None:
            break
        a, b = best
        used.add(tuple(sorted((a, b))))
        counts[a] += 1
        counts[b] += 1
        added.append((a, b))
    return added
