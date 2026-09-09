from datetime import date, datetime
import json


def render_cup_document_import(st, key_prefix, setting):
    """Render review-first document intake and return (prefill, use_teams_key, parsed_date)."""
    prefill_key = f"{key_prefix}_cup_document_prefill"
    use_teams_key = f"{key_prefix}_cup_document_use_teams"
    use_matches_key = f"{key_prefix}_cup_document_use_matches"
    with st.expander("📄 Läs in tidigare cupprogram eller importera från foto/dokument", expanded=False):
        st.caption("Släpp in PDF, TXT eller en bild/skärmdump redan här i första setupsteget. CupNavi läser cupinfo, lag, grupper, matcher, tider, planer, slutspel och regler när de faktiskt finns – och sparar det granskade underlaget så rätt uppgifter kan återanvändas längre fram i setupen.")
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
            render_initial_import_overview(st, extracted)
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
                st.checkbox("Lägg in de hittade lagen när cupen skapas", value=True, key=use_teams_key)
                if groups:
                    st.info(f"📦 {len(groups)} grupp(er) hittade. Gruppindelningen följer med från den här första importen och visas igen på Steg 3 · Grupper för granskning/användning. Du behöver inte läsa in samma foto en gång till.")
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
                    "Använd det granskade matchprogrammet som cupens schema", value=True, key=use_matches_key,
                    help="Standardvalet är att det granskade schemat från foto/PDF följer med cupen. Det låses som befintligt schema och ändras bara om du själv väljer att redigera eller bygga om det.",
                )
                st.info("Det granskade matchprogrammet är förvalt. När cupen skapas blir det cupens befintliga schema och behöver inte läsas in igen. Avmarkera bara om du inte vill använda schemat från underlaget.")
            if playoffs:
                st.markdown("**🏆 Slutspel som CupNavi hittade**")
                rows = []
                for m in playoffs:
                    rows.append({"Tid": m.get("time") or "—", "Match": m.get("label") or "—", "Lag/källa 1": m.get("home_source") or "—", "Lag/källa 2": m.get("away_source") or "—", "Plan": m.get("venue") or "—", "Speltid": m.get("duration") or "—"})
                st.dataframe(rows, use_container_width=True, hide_index=True)
            if extracted.get("venues"):
                st.info("📦 Planer/anläggningar hittades också. De följer med till Steg 5 · Planer & tider för granskning – du behöver inte läsa in underlaget igen.")
            if extracted.get("rules") or any((extracted.get("rule_values") or {}).values()):
                st.markdown("**📘 Regler och praktiska uppgifter som hittades**")
                for rule in extracted.get("rules") or []:
                    st.markdown(f"- {rule}")
                st.caption("Regeluppgifterna följer med till Steg 4 · Regler. Bara uttryckligen avlästa värden kan användas automatiskt; övrig regeltext visas som stöd för din granskning.")
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



def initial_import_overview(prefill):
    """Summarize what the first photo/document scan actually found.

    The overview is deliberately descriptive: `found` means extracted from the
    source, not already written into the tournament. Later setup steps remain
    review-first.
    """
    payload = prefill or {}
    teams = payload.get("teams") or []
    groups = sorted({str((row or {}).get("group_name") or "").strip() for row in teams if str((row or {}).get("group_name") or "").strip()})
    venues = [str(v).strip() for v in (payload.get("venues") or []) if str(v).strip()]
    matches = [row for row in (payload.get("matches") or []) if isinstance(row, dict)]
    playoffs = [row for row in (payload.get("playoff_matches") or []) if isinstance(row, dict)]
    rules = [str(v).strip() for v in (payload.get("rules") or []) if str(v).strip()]
    rule_values = {k: v for k, v in (payload.get("rule_values") or {}).items() if v is not None}
    cupinfo_values = [payload.get("tournament_name"), payload.get("location"), payload.get("start_date"), payload.get("end_date")]
    cupinfo_count = sum(1 for value in cupinfo_values if str(value or "").strip())
    return [
        {"key": "cupinfo", "label": "Cupinfo", "found": cupinfo_count > 0, "detail": f"{cupinfo_count} uppgift(er) hittade" if cupinfo_count else "Inte hittat"},
        {"key": "teams", "label": "Lag", "found": bool(teams), "detail": f"{len(teams)} lag" if teams else "Inte hittat"},
        {"key": "groups", "label": "Grupper", "found": bool(groups), "detail": f"{len(groups)} grupper" if groups else "Inte hittat"},
        {"key": "rules", "label": "Regler", "found": bool(rules or rule_values), "detail": (f"{len(rules)} regeltexter · {len(rule_values)} avlästa värden" if rules and rule_values else f"{len(rules)} regeltexter" if rules else f"{len(rule_values)} avlästa värden") if (rules or rule_values) else "Inte hittat"},
        {"key": "venues", "label": "Planer", "found": bool(venues), "detail": f"{len(venues)} planer/anläggningar" if venues else "Inte hittat"},
        {"key": "schedule", "label": "Schema", "found": bool(matches), "detail": f"{len(matches)} matcher" if matches else "Inte hittat"},
        {"key": "playoffs", "label": "Slutspel", "found": bool(playoffs), "detail": f"{len(playoffs)} matcher" if playoffs else "Inte hittat"},
    ]


def render_initial_import_overview(st, prefill):
    """Render a compact review-first overview after the initial scan."""
    overview = initial_import_overview(prefill)
    st.markdown("#### Importöversikt")
    st.caption("Det här har CupNavi hittat i ditt första underlag. ✓ betyder hittat – inte att uppgiften redan är sparad. Du granskar och använder varje del i rätt setupsteg.")
    found = [row for row in overview if row["found"]]
    missing = [row for row in overview if not row["found"]]
    if found:
        st.success("Hittat i underlaget: " + " · ".join(f"{row['label']} ✓" for row in found))
    if missing:
        st.caption("Behöver kompletteras senare: " + " · ".join(row["label"] for row in missing))
    cols = st.columns(2)
    for index, row in enumerate(overview):
        marker = "✓" if row["found"] else "—"
        cols[index % 2].markdown(f"**{marker} {row['label']}**  \n{row['detail']}")
    warnings = [str(v).strip() for v in (prefill or {}).get("warnings") or [] if str(v).strip()]
    if warnings:
        st.warning(f"{len(warnings)} sak(er) behöver kontrolleras i underlaget innan du går vidare.")
    return overview


def save_setup_import_snapshot(connection_factory, tournament_id, prefill, *, import_kind="initial_setup"):
    """Persist reviewed initial import for reuse by later setup steps."""
    payload = dict(prefill or {})
    if not payload:
        return None
    con = connection_factory()
    try:
        con.execute(
            "DELETE FROM tournament_setup_imports WHERE tournament_id=? AND import_kind=?",
            (tournament_id, import_kind),
        )
        cur = con.execute(
            "INSERT INTO tournament_setup_imports(tournament_id,import_kind,source_name,payload_json) VALUES(?,?,?,?)",
            (
                tournament_id,
                import_kind,
                str(payload.get("source_name") or "Foto/dokument"),
                json.dumps(payload, ensure_ascii=False),
            ),
        )
        con.commit()
        return getattr(cur, "lastrowid", None)
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def load_setup_import_snapshot(connection_factory, tournament_id, *, import_kind="initial_setup"):
    """Return the latest persisted reviewed setup import, or an empty dict."""
    con = connection_factory()
    try:
        row = con.execute(
            "SELECT payload_json FROM tournament_setup_imports WHERE tournament_id=? AND import_kind=? ORDER BY id DESC LIMIT 1",
            (tournament_id, import_kind),
        ).fetchone()
        if not row:
            return {}
        raw = row[0] if not hasattr(row, "keys") else row["payload_json"]
        parsed = json.loads(str(raw or "{}"))
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}
    finally:
        con.close()


def document_group_assignments(prefill):
    """Normalize reviewed team→group pairs from the initial import."""
    out = []
    seen = set()
    for row in (prefill or {}).get("teams") or []:
        team = " ".join(str((row or {}).get("name") or "").split())
        group = " ".join(str((row or {}).get("group_name") or "").split())
        key = (team.casefold(), group.casefold())
        if not team or not group or key in seen:
            continue
        seen.add(key)
        out.append({"name": team, "group_name": group})
    return out



def document_plan_hints(prefill):
    """Return non-destructive plan/time hints carried by the initial import."""
    payload = prefill or {}
    venues = []
    seen = set()
    for value in payload.get("venues") or []:
        name = " ".join(str(value or "").split())
        if name and name.casefold() not in seen:
            seen.add(name.casefold()); venues.append(name)
    match_times = []
    for row in payload.get("matches") or []:
        venue = " ".join(str((row or {}).get("venue") or "").split())
        if venue and venue.casefold() not in seen:
            seen.add(venue.casefold()); venues.append(venue)
        raw = str((row or {}).get("time") or "").strip()
        if raw:
            match_times.append(raw)
    return {"venues": venues, "match_times": match_times}


def document_rule_values(prefill):
    """Return only explicitly extracted structured rule values from initial import."""
    raw = (prefill or {}).get("rule_values") or {}
    allowed = ("halves","minutes_per_half","halftime_minutes","points_win","points_draw","points_loss")
    out = {}
    for key in allowed:
        value = raw.get(key) if isinstance(raw, dict) else None
        if value is None:
            continue
        try:
            out[key] = int(value)
        except (TypeError, ValueError):
            continue
    return out

def apply_document_teams(connection_factory, tournament_id, prefill, *, assign_groups=False):
    """Write reviewed teams atomically; group assignments can be deferred to Step 3."""
    teams = list(prefill.get("teams") or [])
    if not teams:
        return 0
    con = connection_factory()
    try:
        group_ids = {}
        for row in teams:
            group_name = str(row.get("group_name") or "").strip(); group_id = None
            if assign_groups and group_name:
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



def apply_document_groups(connection_factory, tournament_id, prefill):
    """Apply reviewed initial-import grouping later in Step 3 without overwriting existing groups."""
    assignments = document_group_assignments(prefill)
    if not assignments:
        return {"groups": 0, "assigned": 0, "unmatched": []}
    con = connection_factory()
    try:
        existing = con.execute("SELECT COUNT(*) FROM groups WHERE tournament_id=?", (tournament_id,)).fetchone()[0]
        if existing:
            raise ValueError("Cupen har redan grupper. Den första importen används bara som jämförelse och skriver inte över något.")
        teams = con.execute("SELECT id,name,group_id FROM teams WHERE tournament_id=?", (tournament_id,)).fetchall()
        team_map = {str(row[1]).strip().casefold(): (int(row[0]), row[2]) for row in teams}
        group_ids = {}
        unmatched = []
        assigned = 0
        for row in assignments:
            team_name = row["name"]
            group_name = row["group_name"]
            team = team_map.get(team_name.casefold())
            if not team:
                unmatched.append(team_name)
                continue
            gid = group_ids.get(group_name.casefold())
            if gid is None:
                cur = con.execute("INSERT INTO groups(tournament_id,name) VALUES(?,?)", (tournament_id, group_name))
                gid = getattr(cur, "lastrowid", None)
                if not gid:
                    gid = con.execute("SELECT id FROM groups WHERE tournament_id=? AND name=? ORDER BY id DESC LIMIT 1", (tournament_id, group_name)).fetchone()[0]
                group_ids[group_name.casefold()] = int(gid)
            if team[1] is None:
                con.execute("UPDATE teams SET group_id=? WHERE id=? AND tournament_id=? AND group_id IS NULL", (int(gid), int(team[0]), tournament_id))
                assigned += 1
        con.execute("UPDATE tournaments SET schedule_dirty=1 WHERE id=?", (tournament_id,))
        con.commit()
        return {"groups": len(group_ids), "assigned": assigned, "unmatched": unmatched}
    except Exception:
        con.rollback()
        raise
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
