"""Databaslager för schemadomänen.

Modulen känner inte till Streamlit. Appen injicerar:
- fetch_all(sql, params) för läsningar/cache
- connection_factory() för transaktioner
- clear_cache() efter skrivningar
"""


class ScheduleRepository:
    def __init__(self, fetch_all, connection_factory, clear_cache=lambda: None):
        self._fetch_all = fetch_all
        self._connection_factory = connection_factory
        self._clear_cache = clear_cache

    def group_generation_data(self, tournament_id):
        groups = self._fetch_all(
            "SELECT id,name FROM groups WHERE tournament_id=? ORDER BY name",
            (tournament_id,),
        )
        teams = self._fetch_all(
            "SELECT id,group_id FROM teams WHERE tournament_id=? ORDER BY group_id,id",
            (tournament_id,),
        )
        existing = self._fetch_all(
            """SELECT group_id,home_source,away_source
               FROM matches
               WHERE tournament_id=? AND stage='Gruppspel'""",
            (tournament_id,),
        )
        return groups, teams, existing

    def insert_group_matches(self, rows):
        if not rows:
            return
        with self._connection_factory() as con:
            con.executemany(
                """INSERT INTO matches(
                       tournament_id,group_id,stage,match_no,home_source,away_source
                   ) VALUES(?,?,'Gruppspel',?,?,?)""",
                rows,
            )
            con.commit()
        self._clear_cache()

    def scheduling_inputs(self, tournament_id):
        referees = self._fetch_all(
            "SELECT id FROM referees WHERE tournament_id=? ORDER BY name",
            (tournament_id,),
        )
        travel_preferences = self._fetch_all(
            """SELECT id,late_first_match,earliest_first_time
               FROM teams WHERE tournament_id=?""",
            (tournament_id,),
        )
        matches = self._fetch_all(
            """
            SELECT * FROM matches WHERE tournament_id=?
            ORDER BY CASE stage
                WHEN 'Gruppspel' THEN 1 WHEN 'Kvartsfinal' THEN 2
                WHEN 'Semifinal' THEN 3 WHEN 'Bronsmatch' THEN 4
                WHEN 'Final' THEN 5 ELSE 6 END,
                group_id, bracket_id, round_no, match_no
            """,
            (tournament_id,),
        )
        return referees, travel_preferences, matches

    def persist_generated_schedule(
        self,
        tournament_id,
        schedule_updates,
        unresolved,
        preserve_existing,
    ):
        """Spara ett helt schemaläggningspass atomiskt."""
        with self._connection_factory() as con:
            if not preserve_existing:
                con.execute(
                    "UPDATE tournaments SET is_published=0 WHERE id=?",
                    (tournament_id,),
                )
                con.execute(
                    "UPDATE matches SET schedule_published=0 WHERE tournament_id=?",
                    (tournament_id,),
                )
                con.execute(
                    """UPDATE matches
                       SET scheduled_start=NULL,pitch_number=NULL
                       WHERE tournament_id=? AND schedule_locked=0""",
                    (tournament_id,),
                )

            if schedule_updates:
                con.executemany(
                    """UPDATE matches
                       SET scheduled_start=?,pitch_number=?,referee_id=?
                       WHERE id=?""",
                    schedule_updates,
                )

            if unresolved == 0:
                con.execute(
                    "UPDATE tournaments SET schedule_dirty=0 WHERE id=?",
                    (tournament_id,),
                )
            con.commit()
        self._clear_cache()

    def scheduled_matches(self, tournament_id):
        return self._fetch_all(
            """SELECT * FROM matches
               WHERE tournament_id=? AND scheduled_start IS NOT NULL
               ORDER BY scheduled_start,pitch_number,id""",
            (tournament_id,),
        )
