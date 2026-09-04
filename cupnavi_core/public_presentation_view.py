"""Public presentation helpers extracted from app.py in v1.296.

The functions in this module intentionally receive their integration dependencies
from the Streamlit application layer. This keeps presentation logic reusable while
leaving database ownership and domain behavior unchanged.
"""

from __future__ import annotations

import html
from urllib.parse import urlencode

from cupnavi_core.match_status import MATCH_FINISHED, MATCH_HALFTIME, MATCH_LIVE, normalize_match_status

def render_group_table(table_rows, tournament, group_id=None, *, st, group_playoff_qualifiers):
    """Text-TV-inspirerad grupptabell med tydlig markering av slutspelsplatser."""
    if not table_rows:
        st.info("Ingen tabelldata att visa.")
        return
    rows_html = []
    fmt = tournament["playoff_format"]
    qualifier_map = group_playoff_qualifiers(tournament["id"], group_id) if group_id else {}
    for position, (_, data) in enumerate(table_rows, 1):
        qualifier = ""
        row_class = ""
        if position in qualifier_map:
            qualifier_label, row_class = qualifier_map[position]
            if qualifier_label == "A":
                css_class = "a"
            elif qualifier_label == "B":
                css_class = "b"
            elif row_class.startswith("qual-rank-"):
                css_class = row_class.replace("qual-", "")
            else:
                css_class = "playoff"
            qualifier_text = html.escape(str(qualifier_label))
            mobile_qualifier = "✓"
            if row_class.startswith("qual-rank-"):
                rank_value = row_class.rsplit("-", 1)[-1]
                mobile_qualifier = f"{rank_value}:a"
            elif qualifier_label in {"A", "B"}:
                mobile_qualifier = str(qualifier_label)
            qualifier = (
                f"<span class='qualifier {css_class}' title='{qualifier_text}'>"
                f"<span class='qualifier-desktop'>{qualifier_text}</span>"
                f"<span class='qualifier-mobile'>{html.escape(mobile_qualifier)}</span>"
                "</span>"
            )
        elif fmt == "A- och B-slutspel":
            # Fallback before the bracket has been generated.
            if position <= 2:
                qualifier = "<span class='qualifier a'><span class='qualifier-desktop'>A</span><span class='qualifier-mobile'>A</span></span>"
                row_class = "qual-a"
            elif position <= 4:
                qualifier = "<span class='qualifier b'><span class='qualifier-desktop'>B</span><span class='qualifier-mobile'>B</span></span>"
                row_class = "qual-b"
        rows_html.append(
            f"<tr class='{row_class}'><td>{position}</td><td class='team'>{html.escape(str(data['Lag']))}</td>"
            f"<td>{data['S']}</td><td>{data['V']}</td><td>{data['O']}</td><td>{data['F']}</td>"
            f"<td>{data['GM']}</td><td>{data['IM']}</td><td>{data['MS']}</td><td><b>{data['P']}</b></td><td>{qualifier}</td></tr>"
        )
    legend = ""
    if fmt == "A- och B-slutspel":
        legend = "<div class='texttv-legend'><span><i class='a'></i>A-slutspel</span><span><i class='b'></i>B-slutspel</span></div>"
    st.markdown(
        f"""
        <style>
        .texttv-wrap{{overflow-x:auto;border:1px solid #dbe4de;border-radius:12px;background:#fff;padding:0}}
        .texttv-table{{width:100%;border-collapse:collapse;font-family:inherit;color:#172033}}
        .texttv-table th,.texttv-table td{{text-align:center!important;padding:9px 8px;border-bottom:1px solid #e6ece8}}
        .texttv-table th{{background:#f3f7f4;color:#64748b;font-size:11px;letter-spacing:.04em;text-transform:uppercase;font-weight:800}}
        .texttv-table td{{font-size:13px;color:#334155}}
        .texttv-table td:first-child{{font-weight:850;color:#64748b}}
        .texttv-table td.team{{text-align:left!important;font-weight:800;color:#172033}}
        .texttv-table td:nth-child(10){{font-size:15px;color:#172033}}
        .texttv-table tr:last-child td{{border-bottom:0}}
        .texttv-table tr.qual-a td{{background:#dcfce7!important;color:#14532d!important}}
        .texttv-table tr.qual-b td{{background:#dbeafe!important;color:#1e3a8a!important}}
        .texttv-table tr.qual-rank-1 td{{background:#dcfce7!important;color:#14532d!important}}
        .texttv-table tr.qual-rank-2 td{{background:#dbeafe!important;color:#1e3a8a!important}}
        .texttv-table tr.qual-rank-3 td{{background:#fef3c7!important;color:#78350f!important}}
        .texttv-table tr.qual-rank-4 td{{background:#f1f5f9!important;color:#334155!important}}
        .texttv-table tr.qual-playoff td{{background:#fef3c7!important;color:#78350f!important}}
        .qualifier{{display:inline-flex;width:24px;height:24px;align-items:center;justify-content:center;border-radius:4px;color:#fff;font-weight:900}}
        .qualifier.a,.texttv-legend i.a{{background:#16a34a}}
        .qualifier.b,.texttv-legend i.b{{background:#2563eb}}
        .qualifier.rank-1{{background:#15803d;min-width:28px;width:auto;padding:0 6px}}
        .qualifier.rank-2{{background:#2563eb;min-width:28px;width:auto;padding:0 6px}}
        .qualifier.rank-3{{background:#d97706;min-width:28px;width:auto;padding:0 6px}}
        .qualifier.rank-4{{background:#64748b;min-width:28px;width:auto;padding:0 6px}}
        .qualifier.playoff{{background:#d97706;min-width:28px;width:auto;padding:0 6px}}
        .texttv-legend{{display:flex;gap:18px;margin-top:7px;color:#334155;font-size:13px}}
        .texttv-legend span{{display:flex;align-items:center;gap:6px}}
        .texttv-legend i{{width:13px;height:13px;border-radius:2px;display:inline-block}}
        .qualifier-mobile{{display:none}}
        @media(max-width:600px){{
          .texttv-wrap{{overflow-x:hidden;border-width:1px;border-radius:11px}}
          .texttv-table{{table-layout:fixed;font-size:12px}}
          .texttv-table th,.texttv-table td{{padding:8px 4px;white-space:nowrap}}
          .texttv-table th:nth-child(1),.texttv-table td:nth-child(1){{width:27px}}
          .texttv-table th:nth-child(2),.texttv-table td:nth-child(2){{width:42%;text-align:left!important;overflow:hidden;text-overflow:ellipsis}}
          .texttv-table th:nth-child(4),.texttv-table td:nth-child(4),
          .texttv-table th:nth-child(5),.texttv-table td:nth-child(5),
          .texttv-table th:nth-child(6),.texttv-table td:nth-child(6),
          .texttv-table th:nth-child(7),.texttv-table td:nth-child(7),
          .texttv-table th:nth-child(8),.texttv-table td:nth-child(8){{display:none}}
          .texttv-table th:nth-child(3),.texttv-table td:nth-child(3){{width:28px}}
          .texttv-table th:nth-child(9),.texttv-table td:nth-child(9){{width:34px}}
          .texttv-table th:nth-child(10),.texttv-table td:nth-child(10){{width:34px;font-weight:900}}
          .texttv-table th:nth-child(11),.texttv-table td:nth-child(11){{width:52px}}
          .texttv-table th:nth-child(11){{font-size:0}}
          .texttv-table th:nth-child(11)::after{{content:'Vidare';font-size:10px}}
          .qualifier{{min-width:28px!important;width:auto!important;height:22px!important;padding:0 5px!important;font-size:10px!important;line-height:1!important}}
          .qualifier-desktop{{display:none}}
          .qualifier-mobile{{display:inline}}
          .texttv-legend{{gap:9px;font-size:10px;flex-wrap:wrap}}
        }}
        </style>
        <div class="texttv-wrap"><table class="texttv-table">
        <thead><tr><th>Pl</th><th>Lag</th><th>S</th><th>V</th><th>O</th><th>F</th><th>GM</th><th>IM</th><th>MS</th><th>P</th><th>Slutspel</th></tr></thead>
        <tbody>{''.join(rows_html)}</tbody></table></div>{legend}
        """,
        unsafe_allow_html=True,
    )

def render_bracket_tree(
    bracket_id,
    public=False,
    *,
    st,
    all_rows,
    row_value,
    resolve_source,
    source_label,
    match_meta,
    team_by_id=None,
):
    bracket_matches = all_rows("SELECT * FROM matches WHERE bracket_id=? ORDER BY round_no,match_no", (bracket_id,))
    # v320: The public workspace already owns a compact team snapshot. Reuse it
    # for bracket labels/colors instead of querying every team again for each
    # displayed bracket. Admin and standalone callers keep the existing fallback.
    bracket_team_by_id = {int(key): row for key, row in (team_by_id or {}).items()}
    if not bracket_team_by_id and bracket_matches:
        bracket_tournament_id = int(row_value(bracket_matches[0], "tournament_id", 0) or 0)
        if bracket_tournament_id:
            bracket_team_rows = all_rows(
                "SELECT id,name,primary_color,secondary_color FROM teams WHERE tournament_id=? ORDER BY id",
                (bracket_tournament_id,),
            )
            bracket_team_by_id = {int(row["id"]): row for row in bracket_team_rows}
    main_stages = []
    for stage_name in ["Kvartsfinal", "Semifinal", "Final"]:
        stage_matches = [m for m in bracket_matches if m["stage"] == stage_name]
        if stage_matches:
            main_stages.append((stage_name, stage_matches))
    if not main_stages:
        st.info("Slutspelsträdet saknar matcher.")
        return

    # A final-only bracket should be compact instead of reserving a full tree canvas.
    stage_count = len(main_stages)
    first_count = len(main_stages[0][1])
    compact_final_only = stage_count == 1 and first_count == 1
    card_width = 320 if compact_final_only else 250
    card_height = 108
    column_gap = 92
    column_width = card_width + column_gap
    header_height = 44
    if compact_final_only:
        play_height = card_height + 44
        canvas_width = min(520, card_width + 40)
    else:
        play_height = max(250, first_count * 154)
        canvas_width = stage_count * column_width - column_gap + 40
    canvas_height = header_height + play_height + 16

    stage_centers = []
    first_centers = [(index + 0.5) * play_height / first_count for index in range(first_count)]
    stage_centers.append(first_centers)
    for stage_index in range(1, len(main_stages)):
        previous = stage_centers[-1]
        match_count = len(main_stages[stage_index][1])
        centers = []
        for index in range(match_count):
            feeders = previous[index * 2:index * 2 + 2]
            centers.append(sum(feeders) / len(feeders) if feeders else (index + 0.5) * play_height / match_count)
        stage_centers.append(centers)

    def match_card(match_row, left, center, extra_class=""):
        home_id = resolve_source(match_row["home_source"])
        away_id = resolve_source(match_row["away_source"])
        home = bracket_team_by_id.get(int(home_id)) if home_id else None
        away = bracket_team_by_id.get(int(away_id)) if away_id else None
        home_name = html.escape(home["name"] if home is not None else source_label(match_row["home_source"]))
        away_name = html.escape(away["name"] if away is not None else source_label(match_row["away_source"]))
        home_color = home["primary_color"] if home else "#94a3b8"
        away_color = away["secondary_color"] if away else "#94a3b8"
        home_score = "–" if match_row["home_score"] is None else str(match_row["home_score"])
        away_score = "–" if match_row["away_score"] is None else str(match_row["away_score"])
        home_winner = away_winner = False
        if match_row["home_score"] is not None and match_row["away_score"] is not None:
            if match_row["home_score"] > match_row["away_score"]:
                home_winner = True
            elif match_row["away_score"] > match_row["home_score"]:
                away_winner = True
            elif match_row["decided_winner_id"] in (home_id, away_id):
                home_winner = match_row["decided_winner_id"] == home_id
                away_winner = match_row["decided_winner_id"] == away_id
            elif match_row["home_penalties"] is not None and match_row["away_penalties"] is not None:
                home_winner = match_row["home_penalties"] > match_row["away_penalties"]
                away_winner = match_row["away_penalties"] > match_row["home_penalties"]
        if public and not match_row["schedule_published"]:
            schedule_text, referee = "Tid och plan ej publicerade", "Ej publicerad"
        else:
            schedule_text, referee = match_meta(match_row)
        penalties = ""
        if match_row["decided_winner_id"]:
            penalties = "<div class='bracket-penalties'>Avgjord genom lottning</div>"
        elif match_row["home_penalties"] is not None:
            penalties = f"<div class='bracket-penalties'>Straffar {match_row['home_penalties']}–{match_row['away_penalties']}</div>"
        top = header_height + center - card_height / 2
        return f"""
          <div class="classic-match {extra_class}" style="left:{left}px;top:{top:.1f}px;width:{card_width}px;min-height:{card_height}px">
            <div class="classic-meta">{html.escape(schedule_text)}</div>
            <div class="classic-team{' winner' if home_winner else ''}"><i style="background:{home_color}"></i><span>{home_name}</span><b>{home_score}</b></div>
            <div class="classic-team{' winner' if away_winner else ''}"><i style="background:{away_color}"></i><span>{away_name}</span><b>{away_score}</b></div>
            {penalties}<div class="classic-referee">Domare: {html.escape(referee)}</div>
          </div>
        """

    headers = []
    cards = []
    for stage_index, (stage_name, stage_matches) in enumerate(main_stages):
        left = 20 + stage_index * column_width
        if compact_final_only:
            left = max(20, (canvas_width - card_width) / 2)
        trophy = " 🏆" if stage_name == "Final" else ""
        headers.append(f"<div class='classic-stage-title' style='left:{left}px;width:{card_width}px'>{stage_name}{trophy}</div>")
        for match_index, match_row in enumerate(stage_matches):
            cards.append(match_card(match_row, left, stage_centers[stage_index][match_index], "final-match" if stage_name == "Final" else ""))

    connectors = []
    for stage_index in range(len(main_stages) - 1):
        start_x = 20 + stage_index * column_width + card_width
        end_x = 20 + (stage_index + 1) * column_width
        middle_x = (start_x + end_x) / 2
        previous = stage_centers[stage_index]
        following = stage_centers[stage_index + 1]
        for next_index, next_center in enumerate(following):
            feeders = previous[next_index * 2:next_index * 2 + 2]
            if not feeders:
                continue
            top_y = header_height + min(feeders)
            bottom_y = header_height + max(feeders)
            for feeder in feeders:
                y = header_height + feeder
                connectors.append(f"<span class='line horizontal' style='left:{start_x}px;top:{y:.1f}px;width:{middle_x-start_x}px'></span>")
            connectors.append(f"<span class='line vertical' style='left:{middle_x}px;top:{top_y:.1f}px;height:{bottom_y-top_y:.1f}px'></span>")
            target_y = header_height + next_center
            connectors.append(f"<span class='line horizontal' style='left:{middle_x}px;top:{target_y:.1f}px;width:{end_x-middle_x}px'></span>")

    def _winner_flags(match_row, home_id, away_id):
        home_winner = away_winner = False
        if match_row["home_score"] is not None and match_row["away_score"] is not None:
            if match_row["home_score"] > match_row["away_score"]:
                home_winner = True
            elif match_row["away_score"] > match_row["home_score"]:
                away_winner = True
            elif match_row["decided_winner_id"] in (home_id, away_id):
                home_winner = match_row["decided_winner_id"] == home_id
                away_winner = match_row["decided_winner_id"] == away_id
            elif match_row["home_penalties"] is not None and match_row["away_penalties"] is not None:
                home_winner = match_row["home_penalties"] > match_row["away_penalties"]
                away_winner = match_row["away_penalties"] > match_row["home_penalties"]
        return home_winner, away_winner

    def _decider_text(match_row):
        if match_row["decided_winner_id"]:
            return "Avgjord genom lottning"
        if match_row["home_penalties"] is not None and match_row["away_penalties"] is not None:
            return f"Straffar {match_row['home_penalties']}–{match_row['away_penalties']}"
        return ""

    def _mobile_status(match_row):
        has_score = match_row["home_score"] is not None and match_row["away_score"] is not None
        status = normalize_match_status(row_value(match_row, "match_status", None), has_result=False)
        if status == MATCH_LIVE:
            return "Pågår", " live"
        if status == MATCH_HALFTIME:
            return "Paus", " halftime"
        if status == MATCH_FINISHED or (has_score and row_value(match_row, "match_status", None) in (None, "", MATCH_FINISHED)):
            return "Slut", " finished"
        return "Kommande", " upcoming"

    mobile_rounds = []
    # Legacy mobile QA anchor: for stage_name, stage_matches in main_stages:
    for stage_index, (stage_name, stage_matches) in enumerate(main_stages):
        mobile_cards = []
        next_stage = main_stages[stage_index + 1][0] if stage_index + 1 < len(main_stages) else ""
        for match_row in stage_matches:
            home_id = resolve_source(match_row["home_source"])
            away_id = resolve_source(match_row["away_source"])
            home = bracket_team_by_id.get(int(home_id)) if home_id else None
            away = bracket_team_by_id.get(int(away_id)) if away_id else None
            home_name = html.escape(home["name"] if home is not None else source_label(match_row["home_source"]))
            away_name = html.escape(away["name"] if away is not None else source_label(match_row["away_source"]))
            home_score = "–" if match_row["home_score"] is None else str(match_row["home_score"])
            away_score = "–" if match_row["away_score"] is None else str(match_row["away_score"])
            home_winner, away_winner = _winner_flags(match_row, home_id, away_id)
            decider = _decider_text(match_row)
            if public and not match_row["schedule_published"]:
                mobile_meta = "Tid och plan ej publicerade"
            else:
                mobile_meta, _ = match_meta(match_row)
            status_label, status_class = _mobile_status(match_row)
            if stage_name == "Final":
                status_class += " final"
            path_hint = f"Vinnaren går vidare till {next_stage.lower()}" if next_stage else ("Vinnaren tar guldet" if stage_name == "Final" else "")
            match_action = ""
            if public:
                # v449: use the already-supported direct match route. This is a plain
                # relative link, so rendering the mobile bracket adds no callbacks,
                # reruns or database reads. Preserve Min cup when a team is selected.
                direct_params = {
                    "cup": str(row_value(match_row, "tournament_id", "") or ""),
                    "section": "matches",
                    "match": str(match_row["id"]),
                }
                if hasattr(st, "query_params"):
                    requested_team = str(st.query_params.get("team", "") or "").strip()
                    if requested_team:
                        direct_params["team"] = requested_team
                match_href = "?" + urlencode(direct_params)
                action_label = "Följ matchen nu" if status_label in {"Pågår", "Paus"} else "Öppna match"
                match_action = (
                    f"<a class='match-action{' live-action' if status_label in {'Pågår', 'Paus'} else ''}' "
                    f"href='{html.escape(match_href, quote=True)}' target='_self'>"
                    f"{html.escape(action_label)} <span aria-hidden='true'>→</span></a>"
                )
            mobile_cards.append(
                f"<div class='cn-playoff-mobile-match{status_class}'>"
                f"<div class='meta'><span>{html.escape(mobile_meta)}</span><b>{html.escape(status_label)}</b></div>"
                f"<div class='team{' winner' if home_winner else ''}'><span>{home_name}</span><b>{home_score}</b></div>"
                f"<div class='team{' winner' if away_winner else ''}'><span>{away_name}</span><b>{away_score}</b></div>"
                + (f"<div class='decider'>{html.escape(decider)}</div>" if decider else "")
                + (f"<div class='path'>{html.escape(path_hint)}</div>" if path_hint else "")
                + match_action
                + "</div>"
            )
        round_progress = f"<span>{len(stage_matches)} match{'er' if len(stage_matches) != 1 else ''}</span>"
        mobile_rounds.append(
            f"<section class='cn-playoff-mobile-round'><div class='round-head'><h4>{html.escape(stage_name)}</h4>{round_progress}</div>{''.join(mobile_cards)}</section>"
        )
    mobile_bracket_html = f"<div class='cn-playoff-mobile'>{''.join(mobile_rounds)}</div>"

    bronze_matches = [m for m in bracket_matches if m["stage"] == "Bronsmatch"]
    bronze_html = ""
    if bronze_matches:
        bronze = bronze_matches[0]
        bronze_home_id = resolve_source(bronze["home_source"])
        bronze_away_id = resolve_source(bronze["away_source"])
        bronze_home_team = bracket_team_by_id.get(int(bronze_home_id)) if bronze_home_id else None
        bronze_away_team = bracket_team_by_id.get(int(bronze_away_id)) if bronze_away_id else None
        bronze_home_name = html.escape(bronze_home_team["name"] if bronze_home_team is not None else source_label(bronze["home_source"]))
        bronze_away_name = html.escape(bronze_away_team["name"] if bronze_away_team is not None else source_label(bronze["away_source"]))
        bronze_home = "–" if bronze["home_score"] is None else bronze["home_score"]
        bronze_away = "–" if bronze["away_score"] is None else bronze["away_score"]
        bronze_home_winner, bronze_away_winner = _winner_flags(bronze, bronze_home_id, bronze_away_id)
        bronze_decider = _decider_text(bronze)
        bronze_html = f"""
          <div class='classic-bronze'>
            <div><strong>🥉 Bronsmatch</strong><small>Placeringsmatch</small></div>
            <span class='{'winner' if bronze_home_winner else ''}'>{bronze_home_name}</span><b>{bronze_home}</b>
            <span class='{'winner' if bronze_away_winner else ''}'>{bronze_away_name}</span><b>{bronze_away}</b>
            {f"<em>{html.escape(bronze_decider)}</em>" if bronze_decider else ""}
          </div>
        """
    st.markdown(
        f"""
        <style>
          .classic-bracket-scroll {{overflow-x:auto;padding:4px 3px 12px}}
          .classic-bracket {{position:relative;width:{canvas_width}px;min-width:{canvas_width}px;max-width:100%;height:{canvas_height}px;background:#fff;border:1px solid #e2e8f0;border-radius:14px}}
          .classic-stage-title {{position:absolute;top:12px;text-align:center;font-size:14px;font-weight:800;letter-spacing:.04em;text-transform:uppercase;color:#334155}}
          .classic-match {{position:absolute;z-index:2;box-sizing:border-box;background:#fff;border:1px solid #cbd5e1;border-radius:8px;box-shadow:0 3px 10px rgba(15,23,42,.11);overflow:hidden}}
          .classic-match.final-match {{border:2px solid #d4a017;box-shadow:0 4px 14px rgba(180,120,0,.18)}}
          .classic-meta {{padding:5px 9px;background:#0f5132;color:#fff;font-size:10px;font-weight:650;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
          .classic-team {{display:grid;grid-template-columns:12px 1fr 25px;gap:7px;align-items:center;min-height:29px;padding:2px 8px;border-bottom:1px solid #e5e7eb;font-size:13px;color:#334155}}
          .classic-team i {{width:11px;height:18px;border:1px solid #64748b;border-radius:2px}}
          .classic-team span {{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
          .classic-team b {{font-size:15px;text-align:center;color:#0f172a}}
          .classic-team.winner {{background:#ecfdf5;color:#065f46;font-weight:800}}
          .classic-team.winner b {{color:#047857}}
          .classic-referee {{padding:3px 8px;color:#64748b;font-size:9px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
          .bracket-penalties {{position:absolute;right:34px;bottom:3px;color:#9a3412;font-size:9px;font-weight:700}}
          .line {{position:absolute;z-index:1;display:block;box-sizing:border-box}}
          .line.horizontal {{border-top:2px solid #94a3b8}}
          .line.vertical {{border-left:2px solid #94a3b8}}
          .classic-bronze {{display:grid;grid-template-columns:1fr 32px;gap:4px 10px;max-width:330px;margin-top:12px;padding:12px 14px;background:#fffbeb;border:1px solid #fcd34d;border-left:5px solid #b45309;border-radius:9px}}
          .classic-bronze div {{grid-column:1 / 3;display:flex;justify-content:space-between;margin-bottom:4px;color:#92400e}}
          .classic-bronze small {{color:#a16207}}
          .classic-bronze span {{font-size:13px}}
          .classic-bronze span.winner {{font-weight:850;color:#065f46}}
          .classic-bronze b {{text-align:center}}
          .classic-bronze em {{grid-column:1 / 3;font-style:normal;font-size:10px;font-weight:750;color:#9a3412}}
        </style>
        <style>
          .cn-playoff-mobile {{display:none}}
          @media(max-width:680px){{
            .classic-bracket-scroll {{display:none}}
            .cn-playoff-mobile {{display:block}}
            .cn-playoff-mobile-round {{margin:0 0 18px}}
            .cn-playoff-mobile-round .round-head {{display:flex;align-items:center;justify-content:space-between;gap:10px;margin:0 1px 7px}}
            .cn-playoff-mobile-round h4 {{margin:0;font-size:13px;letter-spacing:.05em;text-transform:uppercase;color:#334155}}
            .cn-playoff-mobile-round .round-head>span {{font-size:10px;font-weight:750;color:#64748b;background:#f1f5f9;padding:3px 7px;border-radius:999px}}
            .cn-playoff-mobile-match {{border:1px solid #dbe4de;border-radius:12px;background:#fff;margin:0 0 9px;overflow:hidden;box-shadow:0 2px 8px rgba(15,23,42,.05)}}
            .cn-playoff-mobile-match.live {{border-color:#f59e0b;box-shadow:0 0 0 2px rgba(245,158,11,.11)}}
            .cn-playoff-mobile-match.halftime {{border-color:#fb923c}}
            .cn-playoff-mobile-match.finished {{opacity:.93}}
            .cn-playoff-mobile-match .meta {{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:7px 9px;background:#f3f7f4;color:#475569;font-size:10px;font-weight:700}}
            .cn-playoff-mobile-match .meta span {{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
            .cn-playoff-mobile-match .meta b {{flex:0 0 auto;padding:2px 6px;border-radius:999px;background:#e2e8f0;color:#475569;font-size:9px}}
            .cn-playoff-mobile-match.live .meta b {{background:#fef3c7;color:#92400e}}
            .cn-playoff-mobile-match.halftime .meta b {{background:#ffedd5;color:#9a3412}}
            .cn-playoff-mobile-match.finished .meta b {{background:#dcfce7;color:#166534}}
            .cn-playoff-mobile-match .team {{display:grid;grid-template-columns:1fr 28px;gap:8px;align-items:center;padding:7px 9px;border-top:1px solid #edf1ee;font-size:13px}}
            .cn-playoff-mobile-match .team span {{font-weight:760;color:#172033;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
            .cn-playoff-mobile-match .team b {{font-size:15px;text-align:center;color:#172033}}
            .cn-playoff-mobile-match .team.winner {{background:#ecfdf5}}
            .cn-playoff-mobile-match .team.winner span,
            .cn-playoff-mobile-match .team.winner b {{color:#047857;font-weight:850}}
            .cn-playoff-mobile-match .team.winner span::after {{content:'Vinnare';display:inline-block;margin-left:6px;padding:1px 5px;border-radius:999px;background:#d1fae5;color:#065f46;font-size:8px;font-weight:850;vertical-align:1px}}
            .cn-playoff-mobile-match .decider {{padding:5px 9px;border-top:1px solid #edf1ee;background:#fff7ed;color:#9a3412;font-size:10px;font-weight:750}}
            .cn-playoff-mobile-match .path {{padding:6px 9px;border-top:1px solid #edf1ee;background:#f8fafc;color:#64748b;font-size:9px;font-weight:700}}
            .cn-playoff-mobile-match.final .path {{color:#92400e;background:#fffbeb}}
            .cn-playoff-mobile-match .match-action {{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:8px 9px;border-top:1px solid #e2e8f0;background:#fff;color:#0f5132!important;text-decoration:none!important;font-size:11px;font-weight:850}}
            .cn-playoff-mobile-match .match-action span {{font-size:15px;line-height:1}}
            .cn-playoff-mobile-match .match-action.live-action {{background:#0f5132;color:#fff!important;border-top-color:#0f5132}}
            .classic-bronze {{max-width:none;margin-top:10px}}
          }}
        </style>
        {mobile_bracket_html}
        <div class="classic-bracket-scroll">
          <div class="classic-bracket">{''.join(connectors)}{''.join(headers)}{''.join(cards)}</div>
        </div>
        {bronze_html}
        """,
        unsafe_allow_html=True,
    )

def public_match_events_html(match_id, match_row=None, rows=None, team_names=None, *, all_rows, one_row, row_value, resolve_source, tr):
    """Publika mål/röda kort. Förhämtad data undviker N+1-frågor."""
    if match_row is None:
        match_row = one_row("SELECT home_source, away_source FROM matches WHERE id=?", (match_id,))
    if not match_row:
        return ""

    home_team_id = resolve_source(match_row["home_source"])
    away_team_id = resolve_source(match_row["away_source"])

    if rows is None:
        rows = all_rows(
            """
            SELECT p.name AS player_name, COALESCE(p.is_protected,0) AS is_protected,
                   t.id AS team_id, t.name AS team_name, s.goals, s.red_cards
            FROM player_match_stats s
            JOIN players p ON p.id=s.player_id
            JOIN teams t ON t.id=p.team_id
            WHERE s.match_id=? AND (s.goals > 0 OR s.red_cards > 0)
            ORDER BY p.name
            """,
            (match_id,),
        )
    if not rows:
        return ""

    team_data = {}
    for row in rows:
        team_id = row_value(row, "team_id")
        if team_id is None:
            continue
        team_data.setdefault(team_id, {"name": row_value(row, "team_name", ""), "events": []})
        goals = int(row_value(row, "goals", 0) or 0)
        reds = int(row_value(row, "red_cards", 0) or 0)
        public_player_name = "Skyddad spelare" if bool(row_value(row, "is_protected", 0)) else str(row_value(row, "player_name", "") or "")
        if goals:
            suffix = f" ×{goals}" if goals > 1 else ""
            team_data[team_id]["events"].append(
                f"<span class='cn-event cn-goal'>⚽ {html.escape(public_player_name)}{suffix}</span>"
            )
        if reds:
            suffix = f" ×{reds}" if reds > 1 else ""
            team_data[team_id]["events"].append(
                f"<span class='cn-event cn-red'>🟥 {html.escape(public_player_name)}{suffix}</span>"
            )

    ordered_team_ids = [home_team_id, away_team_id]
    team_blocks = []
    for team_id in ordered_team_ids:
        data = team_data.get(team_id)
        if data:
            name = str(data.get("name") or "")
            events = "".join(data["events"])
        else:
            name = str((team_names or {}).get(team_id, "") or "")
            events = "<span class='cn-no-events'>–</span>"
        team_blocks.append(
            "<div class='cn-event-team'>"
            f"<div class='cn-event-team-name'>{html.escape(name)}</div>"
            f"<div class='cn-events-list'>{events}</div>"
            "</div>"
        )

    return (
        "<div class='cn-match-events'>"
        f"<div class='cn-events-title'>{html.escape(tr('Matchhändelser'))}</div>"
        "<div class='cn-event-teams'>" + "".join(team_blocks) + "</div>"
        "</div>"
    )

def public_rules_html(tournament, rules, *, row_value, sport_profile):
    """Bygg lättlästa publika regler utifrån cupens sparade inställningar."""
    if not rules:
        return ""

    profile = sport_profile(row_value(tournament, "sport", "Fotboll"))
    period_label = str(profile["period_label"])
    halves = int(rules["halves"] or 1)
    minutes = int(rules["minutes_per_half"] or 0)
    halftime = int(rules["halftime_minutes"] or 0)
    pitch_break = int(rules["pitch_break_minutes"] or 0)
    minimum_rest = int(rules["minimum_team_rest_minutes"] or 0)
    avoid_consecutive = bool(rules["avoid_consecutive_matches"])
    consecutive_break = int(rules["consecutive_match_break_minutes"] or 0)
    pitch_count = int(rules["pitch_count"] or 0)

    match_format = f"{minutes} minuter" if halves == 1 else f"{halves} {period_label} × {minutes} minuter"
    halftime_text = "Ingen periodpaus" if halves == 1 or halftime == 0 else f"Paus mellan {period_label}: {halftime} min"

    if tournament["table_tiebreak"] == "Inbördes möten först":
        table_rule = "Vid lika poäng avgör inbördes möten först, därefter målskillnad och gjorda mål."
    else:
        table_rule = "Vid lika poäng avgör målskillnad först, därefter gjorda mål och lagnamn."

    if avoid_consecutive:
        consecutive_rule = (
            "CupNavi försöker undvika att samma lag spelar direkt efter föregående match. "
            f"Om det inte går läggs {consecutive_break} minuters extra paus in."
        )
    else:
        consecutive_rule = "Följdmatcher för samma lag är tillåtna enligt cupens inställningar."

    playoff_format = tournament["playoff_format"] or "Inget slutspel"
    if playoff_format == "Inget slutspel":
        playoff_rule = "Cupen har inget slutspel."
    else:
        tie_rule = tournament["playoff_tie_rule"] or "Straffar direkt"
        if tie_rule == "Förlängning + straffar":
            extra = int(tournament["extra_time_minutes"] or 0)
            deciding = f"Vid oavgjort spelas {extra} minuters förlängning och därefter straffar vid behov."
        elif tie_rule == "Lottning":
            deciding = "Vid oavgjort avgörs slutspelsmatchen genom lottning."
        else:
            deciding = "Vid oavgjort avgörs slutspelsmatchen med straffar direkt."
        bronze = " Bronsmatch spelas." if tournament["bronze_match"] else " Ingen bronsmatch spelas."
        playoff_rule = f"Slutspelsmodell: {playoff_format}. {deciding}{bronze}"

    return f"""
    <div class="cn-rules-grid">
      <div class="cn-rule-card"><div class="cn-rule-icon">⏱️</div><div>
        <strong>Matchtid</strong><span>{html.escape(match_format)}</span><small>{html.escape(halftime_text)}</small>
      </div></div>
      <div class="cn-rule-card"><div class="cn-rule-icon">🏅</div><div>
        <strong>Poäng</strong><span>Vinst {int(tournament["points_win"] or 0)} · Oavgjort {int(tournament["points_draw"] or 0)} · Förlust {int(tournament["points_loss"] or 0)}</span>
      </div></div>
      <div class="cn-rule-card"><div class="cn-rule-icon">📊</div><div>
        <strong>Tabellplacering</strong><span>{html.escape(table_rule)}</span>
      </div></div>
      <div class="cn-rule-card"><div class="cn-rule-icon">🧘</div><div>
        <strong>Lagvila</strong><span>Minsta lagvila: {minimum_rest} minuter.</span><small>{html.escape(consecutive_rule)}</small>
      </div></div>
      <div class="cn-rule-card"><div class="cn-rule-icon">🏟️</div><div>
        <strong>Planer och pauser</strong><span>{pitch_count} {'plan' if pitch_count == 1 else 'planer'} används.</span><small>Paus mellan matcher på samma plan: {pitch_break} min.</small>
      </div></div>
      <div class="cn-rule-card"><div class="cn-rule-icon">🏆</div><div>
        <strong>Slutspel</strong><span>{html.escape(playoff_rule)}</span>
      </div></div>
    </div>
    """

