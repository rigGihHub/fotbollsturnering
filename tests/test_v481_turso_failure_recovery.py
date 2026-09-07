from pathlib import Path

VERSION = "2026.09.07-495-PUBLIC-UX-PDF-II"
APP = Path("app.py").read_text(encoding="utf-8")


def _cloud_block():
    start = APP.index("def _discard_cloud_raw_connection(")
    end = APP.index("def db():", start)
    return APP[start:end]


def test_version_is_v481():
    assert VERSION in APP
    assert Path("VERSION.txt").read_text().strip() == VERSION


def test_failed_cloud_connection_is_discarded():
    block = _cloud_block()
    assert 'st.session_state.pop("_cupnavi_turso_connection", None)' in block


def test_reads_get_exactly_one_reconnect_path():
    block = _cloud_block()
    execute = block[block.index("    def execute("):block.index("    def executemany(")]
    assert "_discard_cloud_raw_connection(self.raw)" in execute
    assert "fresh = _new_cloud_raw_connection()" in execute
    assert 'st.session_state["_cupnavi_turso_connection"] = fresh' in execute
    assert "try:\n                return self.raw.execute(sql, params)" in execute


def test_writes_are_never_auto_retried():
    block = _cloud_block()
    execute = block[block.index("    def execute("):block.index("    def executemany(")]
    assert "if is_write:" in execute
    assert "_discard_cloud_raw_connection(self.raw)" in execute
    assert "raise" in execute
    # Fresh connection creation occurs only after the write branch has raised.
    assert execute.index("raise") < execute.index("fresh = _new_cloud_raw_connection()")


def test_executemany_write_failure_discards_connection():
    block = _cloud_block()
    section = block[block.index("    def executemany("):block.index("    def commit(")]
    assert "_discard_cloud_raw_connection(self.raw)" in section
    assert "self._dirty = False" in section
    assert "raise" in section


def test_commit_failure_is_unknown_outcome_and_not_retried():
    block = _cloud_block()
    section = block[block.index("    def commit("):block.index("    def rollback(")]
    assert "_discard_cloud_raw_connection(self.raw)" in section
    assert "automat-retrya aldrig commiten" in section
    assert "_new_cloud_raw_connection()" not in section
    assert "raise" in section


def test_broken_rollback_does_not_mask_original_failure():
    block = _cloud_block()
    section = block[block.index("    def rollback("):block.index("    def close(")]
    assert "except Exception:" in section
    assert "_discard_cloud_raw_connection(self.raw)" in section
    assert "return None" in section


def test_no_local_fallback_was_added():
    block = _cloud_block()
    assert "sqlite3.connect" not in block
