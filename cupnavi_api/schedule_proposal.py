"""Deterministic, review-first schedule proposals for existing CupNavi matches."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta

_FINGERPRINT_MATCH_KEYS=("id","group_id","match_no","round_no","home_source","away_source","scheduled_start","pitch_number","schedule_locked","home_score","away_score")
_FINGERPRINT_RULE_KEYS=("halves","minutes_per_half","halftime_minutes","pitch_break_minutes","minimum_team_rest_minutes")
_FINGERPRINT_WINDOW_KEYS=("pitch_number","play_date","start_time","end_time","confirmed")


def schedule_proposal_fingerprint(matches:list[dict],rules:dict,windows:list[dict])->str:
    payload={
        "matches":sorted([{key:row.get(key) for key in _FINGERPRINT_MATCH_KEYS} for row in matches],key=lambda row:int(row.get("id") or 0)),
        "rules":{key:rules.get(key) for key in _FINGERPRINT_RULE_KEYS},
        "windows":sorted([{key:row.get(key) for key in _FINGERPRINT_WINDOW_KEYS} for row in windows],key=lambda row:(str(row.get("play_date") or ""),int(row.get("pitch_number") or 0),str(row.get("start_time") or ""),str(row.get("end_time") or ""))),
    }
    encoded=json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(",",":"),default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _team_id(source)->int|None:
    text=str(source or "").strip()
    if not text.startswith("team:"): return None
    try:return int(text.split(":",1)[1])
    except (TypeError,ValueError):return None


def _start(value)->datetime|None:
    if value in (None,""):return None
    try:return datetime.fromisoformat(str(value))
    except (TypeError,ValueError):return None


def _duration_minutes(rules:dict)->int:
    halves=max(1,int(rules.get("halves") or 2));per_half=max(1,int(rules.get("minutes_per_half") or 20));halftime=max(0,int(rules.get("halftime_minutes") or 0))
    return halves*per_half+max(0,halves-1)*halftime


def _slots(windows:list[dict],rules:dict)->list[tuple[datetime,int]]:
    step=timedelta(minutes=_duration_minutes(rules)+max(0,int(rules.get("pitch_break_minutes") or 0)));result=[]
    for window in windows:
        try:
            pitch=int(window["pitch_number"]);first=datetime.fromisoformat(f"{window['play_date']}T{window['start_time']}");last=datetime.fromisoformat(f"{window['play_date']}T{window['end_time']}")
        except (KeyError,TypeError,ValueError):continue
        current=first
        while current<=last:
            result.append((current,pitch));current+=step
    return sorted(set(result),key=lambda item:(item[0],item[1]))


def _teams(row:dict)->tuple[int,...]:
    values=[]
    for source in (row.get("home_source"),row.get("away_source")):
        team_id=_team_id(source)
        if team_id is not None and team_id not in values:values.append(team_id)
    return tuple(values)


def _latest_prior(history:list[tuple[datetime,datetime,int]],start:datetime):
    prior=[item for item in history if item[1]<=start]
    return max(prior,key=lambda item:item[1]) if prior else None


def _quality_score(start:datetime,pitch:int,row:dict,team_history:dict[int,list[tuple[datetime,datetime,int]]],minimum_rest:int,match_minutes:int)->tuple:
    """Bounded soft preferences; hard schedule constraints are checked first.

    Soft quality is intentionally capped below a normal scheduling slot: pitch
    continuity and comfort rest may choose between equal/near-equal alternatives,
    but never postpone a legal match by a complete later slot just for polish.
    """
    plan_changes=0;comfort_penalty=0;teams=_teams(row);comfort_target=minimum_rest+match_minutes
    for team_id in teams:
        prior=_latest_prior(team_history.get(team_id,[]),start)
        if prior is None:continue
        _prior_start,prior_end,prior_pitch=prior
        if prior_pitch!=pitch:plan_changes+=1
        rest=max(0,int((start-prior_end).total_seconds()//60));comfort_penalty+=max(0,comfort_target-rest)
    bounded_comfort=min(comfort_penalty,15*max(1,len(teams)))
    absolute_minutes=start.toordinal()*1440+start.hour*60+start.minute
    soft_cost=plan_changes*7+bounded_comfort
    return (absolute_minutes+soft_cost,absolute_minutes,pitch)


def build_schedule_proposal(matches:list[dict],rules:dict,windows:list[dict])->dict:
    match_minutes=_duration_minutes(rules);pitch_break=max(0,int(rules.get("pitch_break_minutes") or 0));minimum_rest=max(0,int(rules.get("minimum_team_rest_minutes") or 0))
    match_span=timedelta(minutes=match_minutes);pitch_span=timedelta(minutes=match_minutes+pitch_break);rest_span=timedelta(minutes=minimum_rest)
    pitch_busy={};team_busy={};team_history={};preserved=0;unresolved=[];candidates=[]
    for row in matches:
        start=_start(row.get("scheduled_start"))
        if start is not None and row.get("pitch_number") is not None:
            preserved+=1;pitch=int(row["pitch_number"]);pitch_busy.setdefault(pitch,[]).append((start,start+pitch_span))
            for team_id in _teams(row):
                team_busy.setdefault(team_id,[]).append((start,start+match_span));team_history.setdefault(team_id,[]).append((start,start+match_span,pitch))
            continue
        if bool(row.get("played")) or row.get("home_score") is not None or row.get("away_score") is not None:
            unresolved.append({"match_id":int(row["id"]),"reason":"played_without_schedule"});continue
        if bool(row.get("schedule_locked")):
            unresolved.append({"match_id":int(row["id"]),"reason":"locked_without_schedule"});continue
        candidates.append(row)
    candidates.sort(key=lambda row:(int(row.get("round_no") or 0),int(row.get("group_id") or 0),int(row.get("match_no") or 0),int(row["id"])))
    available_slots=_slots(windows,rules);placements=[];quality_plan_changes=0;quality_rest_minutes=[]
    for row in candidates:
        feasible=[]
        for start,pitch in available_slots:
            pitch_end=start+pitch_span
            if any(start<busy_end and pitch_end>busy_start for busy_start,busy_end in pitch_busy.get(pitch,[])):continue
            match_end=start+match_span;team_ok=True
            for team_id in _teams(row):
                for busy_start,busy_end in team_busy.get(team_id,[]):
                    if start<busy_end+rest_span and match_end+rest_span>busy_start:team_ok=False;break
                if not team_ok:break
            if team_ok:feasible.append((_quality_score(start,pitch,row,team_history,minimum_rest,match_minutes),start,pitch))
        if not feasible:
            unresolved.append({"match_id":int(row["id"]),"reason":"no_feasible_slot"});continue
        _score,start,pitch=min(feasible,key=lambda item:item[0]);pitch_busy.setdefault(pitch,[]).append((start,start+pitch_span))
        for team_id in _teams(row):
            prior=_latest_prior(team_history.get(team_id,[]),start)
            if prior is not None:
                _prior_start,prior_end,prior_pitch=prior
                if prior_pitch!=pitch:quality_plan_changes+=1
                quality_rest_minutes.append(max(0,int((start-prior_end).total_seconds()//60)))
            team_busy.setdefault(team_id,[]).append((start,start+match_span));team_history.setdefault(team_id,[]).append((start,start+match_span,pitch))
        placements.append({"match_id":int(row["id"]),"scheduled_start":start.isoformat(timespec="minutes"),"pitch_number":pitch})
    avg_rest=round(sum(quality_rest_minutes)/len(quality_rest_minutes),1) if quality_rest_minutes else None;min_rest=min(quality_rest_minutes) if quality_rest_minutes else None
    return {
        "deterministic":True,"writes_database":False,"fingerprint":schedule_proposal_fingerprint(matches,rules,windows),
        "match_duration_minutes":match_minutes,"pitch_break_minutes":pitch_break,"minimum_team_rest_minutes":minimum_rest,
        "preserved_count":preserved,"candidate_count":len(candidates),"placed_count":len(placements),"unresolved_count":len(unresolved),
        "placements":placements,"unresolved":sorted(unresolved,key=lambda item:item["match_id"]),
        "quality":{"strategy":"bounded_pitch_continuity_and_rest","plan_change_count":quality_plan_changes,"minimum_observed_rest_minutes":min_rest,"average_observed_rest_minutes":avg_rest},
    }
