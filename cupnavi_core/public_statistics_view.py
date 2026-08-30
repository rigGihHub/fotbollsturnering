"""Public tables, rankings, statistics and playoff rendering.

Extracted from app.py in v1.203. Domain/data helpers are injected by app.py so
business behavior remains unchanged.
"""
import time
import pandas as pd
import streamlit as st

def render_public_statistics_section(
    tournament_id,
    tournament,
    published_matches,
    played_matches,
    forced_section=None,
    public_team_by_id=None,
    *,
    perf,
    tr,
    row_value,
    all_rows,
    calculate_all_group_tables,
    render_empty_state,
    render_group_table,
    final_ranking_rows,
    render_centered_table,
    playoff_preview,
    playoff_specs_for_tournament,
    brackets_for_display,
    render_bracket_tree,
):
    """Render one public competition/statistics section without rebuilding the full public page."""
    _fragment_started = time.perf_counter()
    _db_calls_before = perf["db_calls"]
    _db_ms_before = perf["db_ms"]
    _has_toplists = any([
        bool(row_value(tournament, "enable_scorer_leaderboard", 1)),
        bool(row_value(tournament, "enable_assist_leaderboard", 1)),
        bool(row_value(tournament, "enable_card_statistics", 1)),
    ])
    _stats_options = [tr("Tabeller")] + ([tr("Topplistor")] if _has_toplists else []) + [tr("Slutspel")]
    if forced_section:
        stats_section = forced_section
    else:
        stats_section = st.segmented_control(
            tr("Statistik"),
            _stats_options,
            default=tr("Tabeller"),
            key=f"public_stats_section_{tournament_id}",
        ) or tr("Tabeller")

    if stats_section == tr("Tabeller"):
        _public_tables = calculate_all_group_tables(tournament_id, tournament)
        groups = _public_tables["groups"]
        if not groups:
            render_empty_state(
                tr("Inga grupper ännu"),
                tr("När arrangören har publicerat gruppindelningen visas tabellerna här."),
                symbol="—",
            )
        for group in groups:
            st.subheader(group["name"])
            group_table = _public_tables["tables"].get(int(group["id"]), [])
            render_group_table(group_table, tournament, group['id'])
        if bool(row_value(tournament, "enable_final_ranking", 0)):
            st.subheader("Slutlig ranking")
            # v313: ranking is only visible after every published match is complete.
            # Avoid its extra team/playoff/class queries and source resolution while
            # the tournament is still in progress.
            all_done = bool(published_matches) and len(played_matches) == len(published_matches)
            if all_done:
                ranking = final_ranking_rows(tournament_id, tournament)
                if ranking:
                    render_centered_table(pd.DataFrame(ranking))
                else:
                    st.caption("Den slutliga rankingen visas när alla publicerade matcher är färdigspelade.")
            else:
                st.caption("Den slutliga rankingen visas när alla publicerade matcher är färdigspelade.")

    if stats_section == tr("Topplistor") and not _has_toplists:
        st.info("Ingen individuell statistik är aktiverad för den här turneringen.")

    if stats_section == tr("Topplistor") and _has_toplists:
        scorer_enabled = bool(row_value(tournament, "enable_scorer_leaderboard", 1))
        assist_enabled = bool(row_value(tournament, "enable_assist_leaderboard", 1))
        cards_enabled = bool(row_value(tournament, "enable_card_statistics", 1))

        # v318: only return players who can appear in at least one enabled
        # leaderboard. On larger tournaments this avoids transferring and
        # sorting rows whose aggregate statistics are all zero.
        relevant_having = []
        if scorer_enabled:
            relevant_having.append("SUM(COALESCE(s.goals,0)) > 0")
        if assist_enabled:
            relevant_having.append("SUM(COALESCE(s.assists,0)) > 0")
        if cards_enabled:
            relevant_having.append("SUM(COALESCE(s.yellow_cards,0)) > 0 OR SUM(COALESCE(s.red_cards,0)) > 0")
        having_sql = " OR ".join(f"({condition})" for condition in relevant_having)

        rows = all_rows(
            f"""
            SELECT CASE WHEN COALESCE(players.is_protected,0)=1 THEN 'Skyddad spelare' ELSE players.name END AS player_name,
                   teams.name AS team_name,
                   SUM(COALESCE(s.goals,0)) AS goals,SUM(COALESCE(s.assists,0)) AS assists,
                   SUM(COALESCE(s.yellow_cards,0)) AS yellow_cards,SUM(COALESCE(s.red_cards,0)) AS red_cards
            FROM player_match_stats s JOIN players ON players.id=s.player_id
            JOIN teams ON teams.id=players.team_id JOIN matches ON matches.id=s.match_id
            WHERE matches.tournament_id=?
            GROUP BY players.id,players.name,players.is_protected,teams.name
            HAVING {having_sql}
            """,
            (tournament_id,),
        )
        normalized_rows = [
            {
                "player_name": r["player_name"],
                "team_name": r["team_name"],
                "goals": int(r["goals"] or 0),
                "assists": int(r["assists"] or 0),
                "yellow_cards": int(r["yellow_cards"] or 0),
                "red_cards": int(r["red_cards"] or 0),
                "name_sort": str(r["player_name"] or "").lower(),
            }
            for r in rows
        ]

        if scorer_enabled:
            st.subheader(tr("Skytteliga"))
            goal_rows = sorted(
                (r for r in normalized_rows if r["goals"] > 0),
                key=lambda r: (-r["goals"], -r["assists"], r["name_sort"]),
            )
            if goal_rows:
                render_centered_table(pd.DataFrame([{"Pl": i, "Spelare": r["player_name"], "Lag": r["team_name"], "Mål": r["goals"]} for i, r in enumerate(goal_rows, 1)]))
            else:
                st.info(tr("Inga målskyttar har registrerats."))
        if assist_enabled:
            st.subheader(tr("Assistliga"))
            assist_rows = sorted(
                (r for r in normalized_rows if r["assists"] > 0),
                key=lambda r: (-r["assists"], -r["goals"], r["name_sort"]),
            )
            if assist_rows:
                render_centered_table(pd.DataFrame([{"Pl": i, "Spelare": r["player_name"], "Lag": r["team_name"], "Assist": r["assists"]} for i, r in enumerate(assist_rows, 1)]))
            else:
                st.info(tr("Inga assist har registrerats."))

        if cards_enabled:
            st.subheader(tr("Kortstatistik"))
            card_rows = sorted(
                (r for r in normalized_rows if r["yellow_cards"] > 0 or r["red_cards"] > 0),
                key=lambda r: (-(r["yellow_cards"] + r["red_cards"]), -r["red_cards"], r["name_sort"]),
            )
            if card_rows:
                render_centered_table(pd.DataFrame([
                    {
                        "Spelare": r["player_name"],
                        "Lag": r["team_name"],
                        "Gula": r["yellow_cards"],
                        "Röda": r["red_cards"],
                    }
                    for r in card_rows
                ]))
            else:
                st.info(tr("Inga kort har registrerats."))

    if stats_section == tr("Slutspel"):
        # v1.311: Streamlit-expanders are not lazy. The playoff forecast used to
        # rebuild all group tables on every playoff-page rerun even when the
        # forecast expander was collapsed. Keep the forecast available, but only
        # pay for the table calculation when the visitor explicitly asks for it.
        show_playoff_forecast = st.toggle(
            "🔮 Visa slutspelsprognos",
            value=False,
            key=f"public_playoff_forecast_{tournament_id}",
            help="Beräknar vilka lag som skulle mötas om tabellerna slutade som de står just nu.",
        )
        if show_playoff_forecast:
            _forecast_bundle = calculate_all_group_tables(tournament_id, tournament)
            forecast_groups = _forecast_bundle["groups"]
            forecast_tables = {
                group["name"]: _forecast_bundle["tables"].get(int(group["id"]), [])
                for group in forecast_groups
            }
            forecast_lines = playoff_preview(forecast_tables, tournament["playoff_format"])
            if forecast_lines:
                st.caption("Prognosen bygger på tabelläget just nu och uppdateras när resultat registreras.")
                for line in forecast_lines:
                    st.write(f"• {line}")
            else:
                st.caption("Det finns ännu inte tillräckligt med tabellunderlag för en slutspelsprognos.")
        if tournament["playoff_format"] == "Inget slutspel":
            st.info("Arrangören har valt att turneringen inte ska ha något slutspel.")
            brackets = []
        else:
            # v319: An already generated bracket is the source of truth for the
            # public playoff page. Avoid rebuilding/validating the desired playoff
            # specification on every public rerun when there is already something
            # to display. For A/B playoffs that validation alone performs group +
            # team-count queries. Only pay that cost when the bracket is missing
            # and we need to explain why.
            brackets, duplicate_brackets = brackets_for_display(tournament_id)
            if not brackets:
                playoff_specs, playoff_setup_error = playoff_specs_for_tournament(tournament_id, tournament)
                if playoff_setup_error:
                    st.warning(f"Slutspelet kan inte skapas med nuvarande upplägg: {playoff_setup_error}")
                elif playoff_specs:
                    st.warning(
                        "Slutspel är valt men slutspelsträdet har ännu inte skapats. "
                        "Arrangören behöver generera eller regenerera hela schemat."
                    )
                else:
                    st.info("Inget slutspelsträd finns ännu.")
            if duplicate_brackets:
                st.warning("Äldre dubbletter av slutspel finns. Arrangören behöver regenerera schemat.")
        for bracket in brackets:
            st.subheader(bracket["name"])
            render_bracket_tree(bracket["id"], public=True, team_by_id=public_team_by_id)



    st.session_state[f"_public_perf_stats_{tournament_id}"] = {
        "render_ms": round((time.perf_counter() - _fragment_started) * 1000, 1),
        "db_calls": perf["db_calls"] - _db_calls_before,
        "db_ms": round(perf["db_ms"] - _db_ms_before, 1),
    }
