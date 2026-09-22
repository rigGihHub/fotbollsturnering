"""Read-only preflight for safely correcting playoff results in the Next admin."""
from __future__ import annotations

from cupnavi_core.placement_playoffs import draw_match_ids
from cupnavi_core.playoff_dependency_safety import (
    build_dependency_guidance,
    dependency_impact,
    downstream_is_locked,
    recovery_eligibility,
    transitive_downstream_match_ids,
    winner_side,
)
from cupnavi_core.playoff_result_progression import decided_side_from_team_id, prepare_result

from .admin_repository import _has_tournament_access
from .participant_resolution_repository import tournament_participant_resolver
from .repository import all_rows, one


def _value(row, key, default=None):
    return row.get(key, default)


def _event_counts(match_ids):
    ids=tuple(int(x) for x in match_ids)
    if not ids:return {}
    placeholders=','.join('?' for _ in ids)
    try:
        rows=all_rows(
            f"SELECT match_id,COUNT(*) AS count FROM player_match_stats WHERE match_id IN ({placeholders}) GROUP BY match_id",
            ids,
        )
    except Exception:
        return {}
    return {int(row['match_id']):int(row.get('count') or 0) for row in rows}


def playoff_result_correction_impact(account_id:int,tournament_id:int,match_id:int,values:dict):
    if not _has_tournament_access(account_id,tournament_id):return None
    row=one("SELECT * FROM matches WHERE id=? AND tournament_id=?",(int(match_id),int(tournament_id)))
    if not row:return None
    if str(row.get('stage') or '')=='Gruppspel':
        return {'playoff':False,'outcome_changes':False,'blocked':False,'downstream':[],'guidance':[]}

    tournament=one("SELECT * FROM tournaments WHERE id=?",(int(tournament_id),))
    matches=all_rows("SELECT * FROM matches WHERE tournament_id=?",(int(tournament_id),))
    if row["id"] in draw_match_ids(tournament, matches):
        return {'playoff':True,'outcome_changes':False,'blocked':False,'downstream':[],'guidance':[],
                'summary':'Placeringsgruppens tabell räknas om med det korrigerade resultatet.'}
    resolver=tournament_participant_resolver(tournament) if tournament else None
    home=resolver.resolve(row.get('home_source')) if resolver else None
    away=resolver.resolve(row.get('away_source')) if resolver else None
    home_id=home.team_id if home and home.resolved else None
    away_id=away.team_id if away and away.resolved else None
    old_manual=decided_side_from_team_id(row.get('decided_winner_id'),home_team_id=home_id,away_team_id=away_id)
    old_side=winner_side(
        home_score=row.get('home_score'),away_score=row.get('away_score'),
        home_penalties=row.get('home_penalties'),away_penalties=row.get('away_penalties'),
        decided_winner_side=old_manual,
    )
    prepared=prepare_result(
        stage=row.get('stage'),home_score=values.get('home_score'),away_score=values.get('away_score'),
        home_penalties=values.get('home_penalties'),away_penalties=values.get('away_penalties'),
        home_team_id=home_id,away_team_id=away_id,
    )
    new_side=prepared.winner_side
    if prepared.home_score==prepared.away_score and prepared.home_penalties is None and old_manual is not None:
        new_side=old_manual

    all_matches=all_rows("SELECT * FROM matches WHERE tournament_id=?",(int(tournament_id),))
    descendant_ids=transitive_downstream_match_ids(int(match_id),all_matches,row_value=_value)
    counts=_event_counts(descendant_ids)
    wanted=set(descendant_ids)
    downstream=[]
    rows=[]
    for item in all_matches:
        mid=int(item.get('id') or 0)
        if mid not in wanted:continue
        enriched=dict(item);enriched['event_count']=counts.get(mid,0);rows.append(enriched)
        locked=downstream_is_locked(enriched,row_value=_value)
        recoverable,recovery_reason=recovery_eligibility(enriched,row_value=_value)
        downstream.append({
            'id':mid,'stage':enriched.get('stage'),'match_no':enriched.get('match_no'),
            'scheduled_start':enriched.get('scheduled_start'),'home_source':enriched.get('home_source'),
            'away_source':enriched.get('away_source'),'home_score':enriched.get('home_score'),
            'away_score':enriched.get('away_score'),'event_count':enriched.get('event_count',0),
            'locked':locked,'recoverable':recoverable,'recovery_reason':recovery_reason,
        })
    outcome_changes=old_side!=new_side
    impact=dependency_impact(
        old_winner_side=old_side,new_winner_side=new_side,
        downstream_rows=rows if outcome_changes else [],row_value=_value,
    )
    locked_rows=[r for r in rows if int(r.get('id') or 0) in set(impact.downstream_match_ids)]
    guidance=list(build_dependency_guidance(locked_rows,row_value=_value)) if impact.blocked else []
    return {
        'playoff':True,'old_winner_side':old_side,'new_winner_side':new_side,
        'outcome_changes':outcome_changes,'blocked':bool(impact.blocked),
        'downstream_count':len(downstream),'downstream':downstream,'guidance':guidance,
        'summary':(
            'Ändringen byter vilket lag som går vidare och påverkar senare slutspelsmatcher.' if outcome_changes and downstream
            else 'Vinnaren ändras inte av den här korrigeringen.' if not outcome_changes
            else 'Vinnaren ändras, men inga senare matcher är beroende av resultatet.'
        ),
    }
