from datetime import datetime
from cupnavi_core.public_match_feed_logic import classify_public_match_feed, public_match_feed_summary

def row(mid,start,home=None,away=None): return {"id":mid,"scheduled_start":start,"home_score":home,"away_score":away}

def test_feed_classifies_live_upcoming_recent_and_ignores_invalid_start():
    now=datetime.fromisoformat("2026-08-26T12:00:00")
    matches=[row(1,"2026-08-26T11:50:00"),row(2,"2026-08-26T13:00:00"),row(3,"2026-08-26T10:00:00",2,1),row(4,"not-a-date")]
    live,nxt,recent=classify_public_match_feed(matches,now=now,match_duration_minutes=20)
    assert [m["id"] for m in live]==[1]; assert [m["id"] for m in nxt]==[2]; assert [m["id"] for m in recent]==[3]

def test_live_summary_has_priority_over_upcoming():
    s=public_match_feed_summary([{"id":1}],[{"id":2}])
    assert s["is_live"] is True and s["title"]=="Pågår just nu" and s["status"]=="1 pågår"

def test_upcoming_summary_when_no_live_match():
    s=public_match_feed_summary([],[{"id":2},{"id":3}])
    assert s["title"]=="Cupen just nu" and s["status"]=="2 kommande"
