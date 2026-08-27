"""Pure classification logic for the public live/upcoming/recent match feed."""

from datetime import datetime, timedelta


def _value(row, key, default=None):
    try:
        value = row[key]
    except (KeyError, TypeError, IndexError):
        try:
            value = row.get(key, default)
        except AttributeError:
            value = default
    return default if value is None and default is not None else value


def _parse_start(row):
    try:
        return datetime.fromisoformat(str(_value(row, "scheduled_start", "") or ""))
    except (TypeError, ValueError):
        return None


def classify_public_match_feed(matches, *, now, match_duration_minutes, max_next=4, max_recent=4):
    live_now=[]; next_matches=[]; recent_results=[]
    duration=timedelta(minutes=max(0,int(match_duration_minutes or 0)))
    for match in matches:
        start=_parse_start(match)
        played=_value(match,"home_score",None) is not None and _value(match,"away_score",None) is not None
        if played:
            recent_results.append(match)
        elif start:
            if start <= now <= start + duration:
                live_now.append(match)
            elif start > now:
                next_matches.append(match)
    live_now=sorted(live_now,key=lambda row:str(_value(row,"scheduled_start","") or ""))
    next_matches=sorted(next_matches,key=lambda row:str(_value(row,"scheduled_start","") or ""))[:max_next]
    recent_results=sorted(recent_results,key=lambda row:str(_value(row,"scheduled_start","") or ""),reverse=True)[:max_recent]
    return live_now,next_matches,recent_results


def public_match_feed_summary(live_now, next_matches, *, max_cards=3):
    if live_now:
        return {"items":list(live_now[:max_cards]),"is_live":True,"title":"Pågår just nu","subtitle":"Matcher som pågår enligt aktuellt schema.","status":f"{len(live_now)} pågår"}
    if next_matches:
        return {"items":list(next_matches[:max_cards]),"is_live":False,"title":"Cupen just nu","subtitle":"Nästa matcher i turneringen.","status":f"{len(next_matches)} kommande"}
    return {"items":[],"is_live":False,"title":"","subtitle":"","status":""}
