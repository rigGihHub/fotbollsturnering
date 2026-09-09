import sqlite3
from cupnavi_core.rate_limit import consume_rate_limit

def schema(con):
    con.execute("""CREATE TABLE rate_limits(
        scope TEXT NOT NULL,subject_hash TEXT NOT NULL,window_start INTEGER NOT NULL,
        count INTEGER NOT NULL DEFAULT 0,last_seen INTEGER NOT NULL,
        PRIMARY KEY(scope,subject_hash,window_start))""")

def test_rate_limit_allows_then_blocks_and_resets_next_window():
    con=sqlite3.connect(":memory:")
    schema(con)
    assert consume_rate_limit(con,scope="x",subject_hash="abc",limit=2,window_seconds=60,now=120)[0]
    assert consume_rate_limit(con,scope="x",subject_hash="abc",limit=2,window_seconds=60,now=121)[0]
    allowed,retry,count=consume_rate_limit(con,scope="x",subject_hash="abc",limit=2,window_seconds=60,now=122)
    assert not allowed and count==3 and retry==58
    assert consume_rate_limit(con,scope="x",subject_hash="abc",limit=2,window_seconds=60,now=180)[0]
