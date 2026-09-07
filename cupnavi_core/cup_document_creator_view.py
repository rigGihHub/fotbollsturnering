from datetime import date


def render_cup_document_import(st, key_prefix, setting):
    """Render review-first document intake and return (prefill, use_teams_key, parsed_date)."""
    prefill_key = f"{key_prefix}_cup_document_prefill"
    use_teams_key = f"{key_prefix}_cup_document_use_teams"
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
                st.dataframe(rows, use_container_width=True, hide_index=True)
                st.info("Matchprogrammet är ett granskningsförslag. Det skrivs inte automatiskt till spelschemat förrän du har granskat och godkänt det i nästa steg.")
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
                st.session_state.pop(prefill_key, None); st.session_state.pop(use_teams_key, None); st.rerun()
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
