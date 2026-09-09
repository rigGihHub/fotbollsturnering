"""Server-side rate limiting backed by the CupNavi database."""
from __future__ import annotations
import time

def consume_rate_limit(con, *, scope, subject_hash, limit, window_seconds, now=None):
    if limit <= 0 or window_seconds <= 0:
        raise ValueError("limit och window_seconds måste vara positiva.")
    now=int(time.time() if now is None else now)
    window_start=now-(now % int(window_seconds))
    con.execute(
        """INSERT INTO rate_limits(scope,subject_hash,window_start,count,last_seen)
           VALUES(?,?,?,?,?)
           ON CONFLICT(scope,subject_hash,window_start)
           DO UPDATE SET count=rate_limits.count+1,last_seen=excluded.last_seen""",
        (str(scope),str(subject_hash),window_start,1,now),
    )
    row=con.execute(
        "SELECT count FROM rate_limits WHERE scope=? AND subject_hash=? AND window_start=?",
        (str(scope),str(subject_hash),window_start),
    ).fetchone()
    count=int(row[0] if not hasattr(row,"keys") else row["count"])
    retry_after=max(0,window_start+int(window_seconds)-now)
    return count <= int(limit), retry_after, count
