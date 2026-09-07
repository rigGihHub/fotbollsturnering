from datetime import date, datetime


def render_cup_document_import(st, key_prefix, setting):
    """Render review-first document intake and return (prefill, use_teams_key, parsed_date)."""
    prefill_key = f"{key_prefix}_cup_document_prefill"
    use_teams_key = f"{key_prefix}_cup_document_use_teams"
    use_matches_key = f"{key_prefix}_cup_document_use_matches"
    with st.expander("📄 Läs in tidigare cupprogram eller importera från foto/dokument", expanded=False):
        st.caption("Släpp in PDF, TXT eller en bild/skärmdump. CupNavi gör ett granskningsbart cupförslag med cupinfo, lag, grupper, matcher, tider, planer, slutspel och regler när uppgifterna finns i dokumentet.")
        uploads = st.file_uploader(
            "Cupprogram, dokument eller bilder", type=["pdf", "txt", "png", "jpg", "jpeg", "webp"],
            key=f"{key_prefix}_cup_document_upload",
            help="Du kan välja flera bilder/dokument samtidigt. Max 25 MB per fil. Inget sparas i cupen förrän du granskat resultatet och skapar cupen.",
            accept_multiple_files=True,
        )
        if uploads and st.button("✨ Läs dokumenten", key=f"{key_prefix}_analyze_cup_document", type="primary"):
            api_key = setting("OPENAI_API_KEY")
            if not api_key:
                st.warning("AI-tolkningen är inte aktiverad ännu. Lägg en OpenAI API-nyckel som OPENAI_API_KEY i Streamlit Secrets. Nyckeln visas aldrig i CupNavi.")
                st.caption("Streamlit Cloud → appens Settings → Secrets → lägg till: OPENAI_API_KEY = \"sk-...\"")
            else:
                try:
                    from cupnavi_core.ai_cup_document_import import extract_cup_setup_from_documents
                    with st.spinner("CupNavi läser dokumenten …"):
                        documents = [(item.getvalue(), item.name, item.type) for item in uploads]
                        extracted = extract_cup_setup_from_documents(documents, api_key)
                    extracted["source_name"] = ", ".join(item.name for item in uploads)
                    st.session_state[prefill_key] = extracted
                    st.session_state[use_teams_key] = True
                except Exception as exc:
                    st.error(f"Dokumentet kunde inte tolkas: {exc}")
        extracted = st.session_state.get(prefill_key)
        if extracted:
            teams = extracted.get("teams") or []
            groups = sorted({row.get("group_name") for row in teams if row.get("group_name")})
            matches = extracted.get("matches") or []; playoffs = extracted.get("playoff_matches") or []
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Lag", len(teams)); c2.metric("Grupper", len(groups)); c3.metric("Matcher", len(matches)); c4.metric("Slutspel", len(playoffs))
            summary = [v for v in (extracted.get("tournament_name"), extracted.get("location"), extracted.get("start_date")) if v]
            if summary:
                st.success(" · ".join(summary))
            if teams:
                grouped = {}
                for row in teams:
                    grouped.setdefault(row.get("group_name") or "Ingen grupp", []).append(row.get("name"))
                for group_name, names in grouped.items():
                    st.markdown(f"**{group_name}:** " + ", ".join(names))
                st.checkbox("Lägg in de hittade lagen och grupperna när cupen skapas", value=True, key=use_teams_key)
            if matches:
                st.markdown("**📅 Matchprogram som CupNavi hittade**")
                rows = []
                for m in matches:
                    rows.append({"Tid": m.get("time") or "—", "Grupp": m.get("group_name") or "—", "Hemma": m.get("home_team") or "—", "Borta": m.get("away_team") or "—", "Plan": m.get("venue") or "—", "Speltid": m.get("duration") or "—"})
                edited_rows = st.data_editor(
                    rows, use_container_width=True, hide_index=True, num_rows="fixed",
                    key=f"{key_prefix}_cup_document_match_editor",
                    column_config={"Tid": st.column_config.TextColumn(help="HH:MM eller YYYY-MM-DD HH:MM")},
                )
                extracted["matches"] = [
                    {"time": r.get("Tid"), "group_name": r.get("Grupp"), "home_team": r.get("Hemma"),
                     "away_team": r.get("Borta"), "venue": r.get("Plan"), "duration": r.get("Speltid"), "stage": "Gruppspel"}
                    for r in edited_rows
                ]
                st.session_state[prefill_key] = extracted
                st.checkbox(
                    "Skapa det granskade matchprogrammet när cupen skapas", value=False, key=use_matches_key,
                    help="CupNavi använder exakt raderna ovan. Ett importerat matchprogram räknas därefter som ett befintligt schema och skrivs aldrig över automatiskt.",
                )
                st.info("Matchprogrammet skrivs inte automatiskt till spelschemat. Inget schema skapas utan ditt uttryckliga godkännande. Efter importen behandlas matcherna som ett befintligt schema.")
            if playoffs:
                st.markdown("**🏆 Slutspel som CupNavi hittade**")
                rows = []
                for m in playoffs:
                    rows.append({"Tid": m.get("time") or "—", "Match": m.get("label") or "—", "Lag/källa 1": m.get("home_source") or "—", "Lag/källa 2": m.get("away_source") or "—", "Plan": m.get("venue") or "—", "Speltid": m.get("duration") or "—"})
                st.dataframe(rows, use_container_width=True, hide_index=True)
            if extracted.get("rules"):
                st.markdown("**📘 Regler och praktiska uppgifter som hittades**")
                for rule in extracted.get("rules"):
                    st.markdown(f"- {rule}")
            for warning in extracted.get("warnings") or []:
                st.warning(warning)
            if st.button("Rensa dokumenttolkning", key=f"{key_prefix}_clear_cup_document"):
                st.session_state.pop(prefill_key, None); st.session_state.pop(use_teams_key, None); st.session_state.pop(use_matches_key, None); st.rerun()
    prefill = st.session_state.get(prefill_key) or {}
    parsed_date = None
    if prefill.get("start_date"):
        try:
            parsed_date = date.fromisoformat(str(prefill["start_date"]))
        except ValueError:
            pass
    return prefill, prefill_key, use_teams_key, parsed_date


def apply_document_teams(connection_factory, tournament_id, prefill):
    """Write reviewed groups and teams atomically. Never creates matches."""
    teams = list(prefill.get("teams") or [])
    if not teams:
        return 0
    con = connection_factory()
    try:
        group_ids = {}
        for row in teams:
            group_name = str(row.get("group_name") or "").strip(); group_id = None
            if group_name:
                group_id = group_ids.get(group_name.casefold())
                if group_id is None:
                    cur = con.execute("INSERT INTO groups(tournament_id,name) VALUES(?,?)", (tournament_id, group_name))
                    group_id = cur.lastrowid; group_ids[group_name.casefold()] = group_id
            con.execute(
                """INSERT INTO teams(tournament_id,name,group_id,primary_color,secondary_color,home_pattern,home_color_2,away_pattern,away_color_2,distance_km,late_first_match,earliest_first_time,travel_note,avoid_late_group_match) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (tournament_id, str(row.get("name") or "").strip(), group_id, "#111827", "#FFFFFF", "Helfärgad", "#FFFFFF", "Helfärgad", "#111827", 0, 0, None, f"Importerad från {prefill.get('source_name') or 'cupportal'}", 0),
            )
        con.execute("UPDATE tournaments SET schedule_dirty=1 WHERE id=?", (tournament_id,)); con.commit(); return len(teams)
    except Exception:
        con.rollback(); raise
    finally:
        con.close()


def _parse_imported_start(value, fallback_date):
    raw = str(value or "").strip()
    if not raw:
        raise ValueError("En importerad match saknar tid.")
    for fmt in ("%H:%M", "%H.%M"):
        try:
            tm = datetime.strptime(raw, fmt).time()
            return datetime.combine(fallback_date, tm).isoformat(timespec="minutes")
        except ValueError:
            pass
    normalized = raw.replace("T", " ")
    try:
        return datetime.fromisoformat(normalized).isoformat(timespec="minutes")
    except ValueError as exc:
        raise ValueError(f"Ogiltig matchtid: {raw}") from exc


def apply_document_matches(connection_factory, tournament_id, prefill, fallback_date):
    """Create explicitly approved imported group matches atomically; never replaces existing matches."""
    matches = list(prefill.get("matches") or [])
    if not matches:
        return 0
    con = connection_factory()
    try:
        if con.execute("SELECT COUNT(*) FROM matches WHERE tournament_id=?", (tournament_id,)).fetchone()[0]:
            raise ValueError("Cupen har redan ett schema. Importen avbryts utan att ändra något.")
        teams = con.execute("SELECT id,name,group_id FROM teams WHERE tournament_id=?", (tournament_id,)).fetchall()
        team_map = {str(r[1]).strip().casefold(): (int(r[0]), r[2]) for r in teams}
        groups = con.execute("SELECT id,name FROM groups WHERE tournament_id=?", (tournament_id,)).fetchall()
        group_map = {str(r[1]).strip().casefold(): int(r[0]) for r in groups}
        pitch_rows = con.execute("SELECT pitch_number,name FROM pitches WHERE tournament_id=?", (tournament_id,)).fetchall()
        pitch_map = {str(r[1]).strip().casefold(): int(r[0]) for r in pitch_rows}
        next_pitch = max([int(r[0]) for r in pitch_rows] or [0]) + 1
        prepared = []
        for no, row in enumerate(matches, start=1):
            home_name = str(row.get("home_team") or "").strip(); away_name = str(row.get("away_team") or "").strip()
            if home_name.casefold() not in team_map or away_name.casefold() not in team_map:
                raise ValueError(f"Match {no} har ett lag som inte finns bland de granskade lagen.")
            home_id, home_gid = team_map[home_name.casefold()]; away_id, away_gid = team_map[away_name.casefold()]
            group_name = str(row.get("group_name") or "").strip()
            group_id = group_map.get(group_name.casefold()) if group_name else home_gid
            if not group_id or home_gid != group_id or away_gid != group_id:
                raise ValueError(f"Match {no} har en grupp som inte stämmer med lagen.")
            venue = str(row.get("venue") or "").strip()
            if not venue:
                raise ValueError(f"Match {no} saknar plan.")
            pitch_no = pitch_map.get(venue.casefold())
            if pitch_no is None:
                pitch_no = next_pitch; next_pitch += 1; pitch_map[venue.casefold()] = pitch_no
                con.execute("INSERT INTO pitches(tournament_id,pitch_number,name) VALUES(?,?,?)", (tournament_id,pitch_no,venue))
            start = _parse_imported_start(row.get("time"), fallback_date)
            prepared.append((tournament_id, group_id, no, f"team:{home_id}", f"team:{away_id}", start, pitch_no))
        con.executemany(
            """INSERT INTO matches(tournament_id,group_id,stage,match_no,home_source,away_source,scheduled_start,pitch_number,schedule_locked)
               VALUES(?,?,'Gruppspel',?,?,?,?,?,1)""", prepared)
        con.execute("UPDATE tournaments SET schedule_dirty=0,is_published=0 WHERE id=?", (tournament_id,))
        con.commit(); return len(prepared)
    except Exception:
        con.rollback(); raise
    finally:
        con.close()
