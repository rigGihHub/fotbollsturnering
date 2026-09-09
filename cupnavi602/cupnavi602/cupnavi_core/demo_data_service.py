from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import os
import random
from typing import Any, Callable


@dataclass(frozen=True)
class DemoDataDeps:
    all_rows: Callable[..., list]
    one_row: Callable[..., Any]
    run: Callable[..., Any]
    db: Callable[..., Any]
    resolve_source: Callable[[Any], Any]
    clear_render_query_cache: Callable[[], None]
    is_test_environment: Callable[[Any], bool]
    ensure_tournament_day_windows: Callable[..., Any]
    ensure_pitch_day_windows: Callable[..., Any]
    create_all_group_matches: Callable[[int], Any]
    ensure_playoffs_for_schedule: Callable[..., tuple]
    generate_schedule: Callable[..., tuple]
    add_feed_item: Callable[..., Any]
    rows_from_cursor: Callable[[Any], list]


class DemoDataService:
    """Isolerad motor för CupNavis test-/demodata.

    Klassen innehåller ingen Streamlit-state. Alla app-/DB-beroenden injiceras så
    att logiken kan testas separat och app.py kan behålla tunna kompatibilitetswrappers.
    """

    def __init__(self, deps: DemoDataDeps):
        self.d = deps

    @staticmethod
    def distribute_count(total, players):
        if total <= 0 or not players:
            return {}
        counts = {player["id"]: 0 for player in players}
        for _ in range(total):
            chosen = random.choice(players)
            counts[chosen["id"]] += 1
        return {player_id: count for player_id, count in counts.items() if count}

    def write_match_stats(self, match_id, team_id, goals, con):
        players = self.d.rows_from_cursor(
            con.execute(
                "SELECT id,name FROM players WHERE team_id=? ORDER BY player_number,name",
                (team_id,),
            )
        )
        if not players:
            return 0

        goal_map = self.distribute_count(goals, players)
        assist_total = random.randint(0, goals) if goals > 0 else 0
        assist_map = self.distribute_count(assist_total, players)
        yellow_total = random.choices([0, 1, 2, 3], weights=[45, 35, 15, 5], k=1)[0]
        red_total = random.choices([0, 1], weights=[92, 8], k=1)[0]
        yellow_map = self.distribute_count(yellow_total, players)
        red_map = self.distribute_count(red_total, players)

        all_player_ids = set(goal_map) | set(assist_map) | set(yellow_map) | set(red_map)
        for player_id in all_player_ids:
            con.execute(
                """
                INSERT INTO player_match_stats(match_id,player_id,goals,assists,yellow_cards,red_cards)
                VALUES(?,?,?,?,?,?)
                ON CONFLICT(match_id,player_id)
                DO UPDATE SET goals=excluded.goals,
                              assists=excluded.assists,
                              yellow_cards=excluded.yellow_cards,
                              red_cards=excluded.red_cards
                """,
                (
                    match_id,
                    player_id,
                    goal_map.get(player_id, 0),
                    assist_map.get(player_id, 0),
                    yellow_map.get(player_id, 0),
                    red_map.get(player_id, 0),
                ),
            )
        return len(all_player_ids)

    def generate_group_results(self, tournament_id, *, fraction=1.0):
        group_matches = self.d.all_rows(
            """SELECT * FROM matches
               WHERE tournament_id=? AND stage='Gruppspel'
               ORDER BY COALESCE(scheduled_start,''),group_id,match_no,id""",
            (tournament_id,),
        )
        if not group_matches:
            return 0, 0, "Inga gruppspelsmatcher finns ännu. Generera spelschemat först."

        fraction = max(0.0, min(1.0, float(fraction)))
        target_count = len(group_matches) if fraction >= 1.0 else max(1, int((len(group_matches) * fraction) + 0.5))
        selected_matches = group_matches[:target_count]
        generated = 0
        stat_rows = 0
        with self.d.db() as con:
            for match_row in selected_matches:
                home_id = self.d.resolve_source(match_row["home_source"])
                away_id = self.d.resolve_source(match_row["away_source"])
                if not home_id or not away_id:
                    continue

                home_score = random.choices([0, 1, 2, 3, 4, 5], weights=[14, 25, 25, 19, 11, 6], k=1)[0]
                away_score = random.choices([0, 1, 2, 3, 4, 5], weights=[16, 27, 24, 18, 10, 5], k=1)[0]
                con.execute(
                    """UPDATE matches
                       SET home_score=?,away_score=?,home_penalties=NULL,away_penalties=NULL,decided_winner_id=NULL
                       WHERE id=?""",
                    (home_score, away_score, match_row["id"]),
                )
                con.execute("DELETE FROM player_match_stats WHERE match_id=?", (match_row["id"],))
                stat_rows += self.write_match_stats(match_row["id"], home_id, home_score, con)
                stat_rows += self.write_match_stats(match_row["id"], away_id, away_score, con)
                generated += 1
            con.commit()

        self.d.clear_render_query_cache()
        return generated, stat_rows, None

    def generate_playoff_results(self, tournament_id, *, fraction=1.0):
        playoff_matches = self.d.all_rows(
            """SELECT * FROM matches
               WHERE tournament_id=? AND stage<>'Gruppspel'
               ORDER BY round_no,match_no,id""",
            (tournament_id,),
        )
        if not playoff_matches:
            return 0, 0, "Inga slutspelsmatcher finns ännu. Generera spelschemat först."

        fraction = max(0.0, min(1.0, float(fraction)))
        target_count = len(playoff_matches) if fraction >= 1.0 else max(1, int((len(playoff_matches) * fraction) + 0.5))
        playoff_matches = playoff_matches[:target_count]
        tournament_row = self.d.one_row("SELECT * FROM tournaments WHERE id=?", (tournament_id,))
        tie_rule = tournament_row["playoff_tie_rule"] or "Straffar direkt"
        generated = 0
        stat_rows = 0
        skipped = 0

        for match_stub in playoff_matches:
            self.d.clear_render_query_cache()
            match_row = self.d.one_row("SELECT * FROM matches WHERE id=?", (match_stub["id"],))
            home_id = self.d.resolve_source(match_row["home_source"])
            away_id = self.d.resolve_source(match_row["away_source"])
            if not home_id or not away_id:
                skipped += 1
                continue

            if random.random() < 0.25:
                score = random.choice([0, 1, 2, 3])
                home_score = away_score = score
            else:
                home_score = random.choices([0, 1, 2, 3, 4], weights=[15, 28, 27, 20, 10], k=1)[0]
                away_score = random.choices([0, 1, 2, 3, 4], weights=[15, 28, 27, 20, 10], k=1)[0]
                if home_score == away_score:
                    if random.random() < 0.5:
                        home_score += 1
                    else:
                        away_score += 1

            home_penalties = away_penalties = decided_winner_id = None
            if home_score == away_score:
                if tie_rule == "Lottning":
                    decided_winner_id = random.choice([home_id, away_id])
                else:
                    winner_home = random.random() < 0.5
                    base = random.randint(3, 5)
                    if winner_home:
                        home_penalties, away_penalties = base, base - 1
                    else:
                        home_penalties, away_penalties = base - 1, base

            with self.d.db() as con:
                con.execute(
                    """UPDATE matches
                       SET home_score=?,away_score=?,home_penalties=?,away_penalties=?,decided_winner_id=?
                       WHERE id=?""",
                    (
                        home_score,
                        away_score,
                        home_penalties,
                        away_penalties,
                        decided_winner_id,
                        match_row["id"],
                    ),
                )
                con.execute("DELETE FROM player_match_stats WHERE match_id=?", (match_row["id"],))
                stat_rows += self.write_match_stats(match_row["id"], home_id, home_score, con)
                stat_rows += self.write_match_stats(match_row["id"], away_id, away_score, con)
                con.commit()

            self.d.clear_render_query_cache()
            generated += 1

        warning = None
        if skipped:
            warning = (
                f"{skipped} slutspelsmatcher kunde inte fyllas eftersom deltagande lag ännu inte kunde avgöras. "
                "Kontrollera att gruppspelet är färdigspelat och kör sedan knappen igen."
            )
        return generated, stat_rows, warning

    def reset_results(self, tournament_id):
        with self.d.db() as con:
            con.execute(
                """DELETE FROM player_match_stats
                   WHERE match_id IN (SELECT id FROM matches WHERE tournament_id=?)""",
                (tournament_id,),
            )
            con.execute(
                """UPDATE matches SET home_score=NULL,away_score=NULL,home_penalties=NULL,away_penalties=NULL,decided_winner_id=NULL
                   WHERE tournament_id=?""",
                (tournament_id,),
            )
            con.commit()
        self.d.clear_render_query_cache()

    def apply_safe_schedule_capacity(self, tournament_id, tournament_row):
        if not self.d.is_test_environment(tournament_row):
            return self.d.one_row("SELECT * FROM schedule_rules WHERE tournament_id=?", (tournament_id,))

        self.d.run(
            """UPDATE schedule_rules
               SET pitch_count=CASE WHEN pitch_count < 8 THEN 8 ELSE pitch_count END,
                   first_match_time='07:00',
                   latest_kickoff_time='23:00',
                   pitch_break_minutes=0,
                   avoid_consecutive_matches=0,
                   consecutive_match_break_minutes=0,
                   referee_mode='Manuell'
               WHERE tournament_id=?""",
            (tournament_id,),
        )
        self.d.run("DELETE FROM pitch_day_windows WHERE tournament_id=?", (tournament_id,))
        self.d.run("DELETE FROM tournament_day_windows WHERE tournament_id=?", (tournament_id,))
        rules_row = self.d.one_row("SELECT * FROM schedule_rules WHERE tournament_id=?", (tournament_id,))
        self.d.ensure_tournament_day_windows(
            tournament_id,
            tournament_row,
            rules_row["first_match_time"],
            rules_row["latest_kickoff_time"],
        )
        self.d.ensure_pitch_day_windows(
            tournament_id,
            tournament_row,
            int(rules_row["pitch_count"]),
            rules_row["first_match_time"],
            rules_row["latest_kickoff_time"],
        )
        return self.d.one_row("SELECT * FROM schedule_rules WHERE tournament_id=?", (tournament_id,))

    def prepare_schedule(self, tournament_id):
        tournament_row = self.d.one_row("SELECT * FROM tournaments WHERE id=?", (tournament_id,))
        rules_row = self.d.one_row("SELECT * FROM schedule_rules WHERE tournament_id=?", (tournament_id,))
        if rules_row is None:
            self.d.run("INSERT INTO schedule_rules(tournament_id) VALUES(?)", (tournament_id,))
            rules_row = self.d.one_row("SELECT * FROM schedule_rules WHERE tournament_id=?", (tournament_id,))

        if os.environ.get("CUPNAVI_E2E") == "1" and self.d.is_test_environment(tournament_row):
            rules_row = self.apply_safe_schedule_capacity(tournament_id, tournament_row)

        self.d.create_all_group_matches(tournament_id)
        playoff_ok, playoff_error = self.d.ensure_playoffs_for_schedule(tournament_id, tournament_row)
        if not playoff_ok:
            return False, playoff_error

        _, unresolved, warning = self.d.generate_schedule(tournament_id, tournament_row, rules_row)
        if unresolved and self.d.is_test_environment(tournament_row):
            rules_row = self.apply_safe_schedule_capacity(tournament_id, tournament_row)
            _, unresolved, retry_warning = self.d.generate_schedule(tournament_id, tournament_row, rules_row)
            warning = retry_warning or warning

        if unresolved:
            return False, warning or f"{unresolved} matcher kunde inte schemaläggas."
        return True, warning

    def apply_progress_level(self, tournament_id, level):
        ok, warning = self.prepare_schedule(tournament_id)
        if not ok:
            return False, warning

        self.reset_results(tournament_id)
        now_iso = datetime.now().isoformat(timespec="seconds")
        self.d.run(
            "UPDATE tournaments SET is_published=1,lifecycle_status='live',completed_at=NULL WHERE id=?",
            (tournament_id,),
        )

        if level == "half_group":
            group_generated, _, group_warning = self.generate_group_results(tournament_id, fraction=0.5)
            return True, group_warning or f"Halva gruppspelet är testspelat ({group_generated} matcher)."

        group_generated, _, group_warning = self.generate_group_results(tournament_id, fraction=1.0)
        if group_warning:
            return False, group_warning
        if level == "full_group":
            return True, f"Hela gruppspelet är testspelat ({group_generated} matcher). Slutspel återstår."

        playoff_fraction = 0.5 if level == "half_playoff" else 1.0
        playoff_generated, _, playoff_warning = self.generate_playoff_results(tournament_id, fraction=playoff_fraction)
        if level == "half_playoff":
            return True, playoff_warning or f"Gruppspelet och halva slutspelet är testspelat ({playoff_generated} slutspelsmatcher)."
        if playoff_warning:
            return False, playoff_warning

        self.d.run(
            "UPDATE tournaments SET lifecycle_status='completed',completed_at=? WHERE id=?",
            (now_iso, tournament_id),
        )
        self.d.add_feed_item(
            tournament_id,
            "Democupen är färdigspelad",
            "Alla grupp- och slutspelsmatcher har testresultat.",
            category="Resultat",
            public=True,
        )
        return True, f"Hela cupen är färdigspelad i testdata ({group_generated} gruppmatcher, {playoff_generated} slutspelsmatcher)."
