"""Streamlit orchestration for the restricted participant/team portal.

Persistence and concurrency-sensitive writers stay injected from app.py.
"""

from dataclasses import dataclass
from datetime import datetime
import html
from typing import Callable

import streamlit as st

from cupnavi_core.notification_service import new_token
from cupnavi_core.team_portal import verify_access_code, squad_deadline_at, squad_is_locked
from cupnavi_core.team_portal_readiness import build_team_portal_readiness, readiness_icon
from cupnavi_core.team_portal_repository import (
    fetch_match_rosters,
    fetch_portal_credential,
    fetch_portal_matches,
    fetch_portal_teams,
    fetch_received_messages,
    fetch_sent_messages,
    fetch_team_players,
)


@dataclass(frozen=True)
class TeamPortalDependencies:
    all_rows: Callable
    one_row: Callable
    participant_role_label: Callable
    row_value: Callable
    team_value: Callable
    match_team_ids: Callable
    portal_match_label: Callable
    team_checkin_snapshot: Callable
    set_team_checkin_if_unchanged: Callable
    team_kit_snapshot: Callable
    confirm_team_kit_if_unchanged: Callable
    team_contact_snapshot: Callable
    save_team_contact_if_unchanged: Callable
    add_team_player_if_capacity: Callable
    player_display_name: Callable
    player_snapshot: Callable
    update_team_player_if_unchanged: Callable
    delete_team_player_if_unchanged: Callable
    save_match_roster_if_unchanged: Callable
    send_team_message: Callable
    mark_team_messages_read: Callable
    message_party_label: Callable
    record_audit: Callable
    kit_preview_html: Callable
    swedish_datetime: Callable


def render_team_portal_workspace(tournament_id, tournament, deps: TeamPortalDependencies):
    """Begränsad portal för ett enda lag/deltagare i en enda cup."""
    role_label = deps.participant_role_label(tournament)
    st.title(f"👥 {role_label} · {tournament['name']}")
    st.caption("Portalen ger endast åtkomst till det egna laget/deltagaren. Resultat och officiella matchhändelser rapporteras av matchrapportör eller domare.")

    teams = fetch_portal_teams(deps.all_rows, tournament_id)
    if not teams:
        st.info("Det finns ännu inga deltagare/lag i cupen.")
        return

    auth = st.session_state.get("participant_portal_auth") or {}
    authenticated_team_id = auth.get("team_id") if auth.get("tournament_id") == tournament_id else None
    valid_team_ids = {int(row["id"]) for row in teams}
    if authenticated_team_id not in valid_team_ids:
        authenticated_team_id = None

    if not authenticated_team_id:
        with st.form(f"participant_login_{tournament_id}"):
            selected_team_id = st.selectbox(
                "Välj lag/deltagare",
                [row["id"] for row in teams],
                format_func=lambda team_id: next(row["name"] for row in teams if row["id"] == team_id),
            )
            code = st.text_input("Lagkod / deltagarkod", type="password", max_chars=12)
            submitted = st.form_submit_button("Logga in", type="primary", use_container_width=True)
        if submitted:
            credential = fetch_portal_credential(deps.one_row, tournament_id, selected_team_id)
            if credential and verify_access_code(code, credential["code_salt"], credential["code_hash"]):
                st.session_state["participant_portal_auth"] = {
                    "tournament_id": int(tournament_id), "team_id": int(selected_team_id)
                }
                st.rerun()
            st.error("Fel kod, eller så har laget ännu ingen kod. Kontakta cupadministratören.")
        return

    team_row = next(row for row in teams if int(row["id"]) == int(authenticated_team_id))
    team_id = int(team_row["id"])
    top1, top2 = st.columns([3, 1])
    top1.markdown(f"**{html.escape(team_row['name'])}**")
    top1.caption("Inloggad i lagportalen")
    if top2.button("Logga ut", key=f"participant_logout_{tournament_id}_{team_id}", use_container_width=True):
        st.session_state.pop("participant_portal_auth", None)
        st.rerun()

    received_messages = fetch_received_messages(deps.all_rows, tournament_id, team_id)
    unread_team_count = sum(1 for row in received_messages if not row["read_at"])
    message_tab_label = f"🔴 Meddelanden ({unread_team_count})" if unread_team_count else "Meddelanden"

    # v373: fetch the core team-day snapshot once and reuse it in all tabs.
    players = fetch_team_players(deps.all_rows, team_id)
    team_matches = fetch_portal_matches(
        deps.all_rows, tournament_id, team_id, deps.match_team_ids
    )
    roster_rows = fetch_match_rosters(deps.all_rows, team_id)
    _portal_readiness = build_team_portal_readiness(
        team_row,
        players=players,
        team_matches=team_matches,
        roster_rows=roster_rows,
        enable_team_checkin=bool(deps.row_value(tournament, "enable_team_checkin", 1)),
        now=datetime.now(),
    )

    st.markdown("### Redo för cupdagen")
    if _portal_readiness["ready"]:
        st.success(
            f"Klart · {_portal_readiness['ready_count']} av {_portal_readiness['actionable_count']} punkter färdiga.",
            icon="✅",
        )
    else:
        st.progress(
            _portal_readiness["ready_count"] / max(1, _portal_readiness["actionable_count"])
        )
        st.caption(
            f"{_portal_readiness['ready_count']} av {_portal_readiness['actionable_count']} klara"
        )
        if _portal_readiness["next_item"]:
            _next = _portal_readiness["next_item"]
            st.info(
                f"Nästa steg: {_next['label']} · {_next['detail']} "
                f"Gå till fliken **{_next['tab']}**."
            )

    _readiness_cols = st.columns(2)
    for _index, _item in enumerate(_portal_readiness["items"]):
        _col = _readiness_cols[_index % 2]
        _col.markdown(
            f"**{readiness_icon(_item['state'])} {_item['label']}**  \n"
            f"{_item['detail']}"
        )

    portal_tabs = st.tabs(["Lag & matcher", "Trupp", "Matchtrupper", message_tab_label])

    with portal_tabs[0]:
        st.caption("Checka in laget, bekräfta matchställ och se kommande matcher.")
        c1, c2 = st.columns(2)
        if bool(deps.row_value(tournament, "enable_team_checkin", 1)):
            if bool(team_row["checked_in"]):
                c1.success(f"✅ Incheckad {team_row['checked_in_at'] or ''}" + (f" av {team_row['checked_in_by']}" if team_row["checked_in_by"] else ""))
                if c1.button("Ta bort incheckning", key=f"portal_uncheck_{team_id}"):
                    saved, reason = deps.set_team_checkin_if_unchanged(
                        team_id,
                        deps.team_checkin_snapshot(team_row),
                        checked_in=False,
                    )
                    if saved:
                        deps.record_audit(tournament_id, "team_checkin", "team", f"{team_row['name']}: incheckning borttagen", entity_id=team_id, actor=role_label)
                    else:
                        st.warning("Lagets incheckningsstatus ändrades av någon annan. Senaste status laddas om.")
                    st.rerun()
            else:
                checkin_name = c1.text_input("Vem checkar in laget?", placeholder="Namn", key=f"checkin_name_{team_id}")
                if c1.button("✅ Vi är på plats", type="primary", key=f"portal_check_{team_id}", use_container_width=True):
                    saved, reason = deps.set_team_checkin_if_unchanged(
                        team_id,
                        deps.team_checkin_snapshot(team_row),
                        checked_in=True,
                        checked_in_by=checkin_name.strip() or role_label,
                    )
                    if saved:
                        deps.record_audit(tournament_id, "team_checkin", "team", f"{team_row['name']}: incheckad", entity_id=team_id, actor=role_label)
                    else:
                        st.warning("Lagets incheckningsstatus ändrades av någon annan. Senaste status laddas om.")
                    st.rerun()
        else:
            c1.caption("Lagincheckning används inte i den här turneringen.")

        if team_row["kit_confirmed_at"]:
            c2.success(f"👕 Matchställ bekräftade {team_row['kit_confirmed_at']}")
        else:
            c2.caption("👕 Matchställ är ännu inte bekräftade.")
        c2.markdown(deps.kit_preview_html(deps.team_value(team_row, "home_pattern", "Helfärgad"), team_row["primary_color"], deps.team_value(team_row, "home_color_2", "#FFFFFF"), "Hemmaställ"), unsafe_allow_html=True)
        c2.markdown(deps.kit_preview_html(deps.team_value(team_row, "away_pattern", "Helfärgad"), team_row["secondary_color"], deps.team_value(team_row, "away_color_2", "#111827"), "Bortaställ"), unsafe_allow_html=True)
        if c2.button(
            "Bekräfta matchställ",
            key=f"confirm_kit_{team_id}",
            use_container_width=True,
            disabled=bool(team_row["kit_confirmed_at"]),
        ):
            saved, reason = deps.confirm_team_kit_if_unchanged(
                team_id,
                deps.team_kit_snapshot(team_row),
            )
            if saved:
                deps.record_audit(tournament_id, "kit_confirmed", "team", f"{team_row['name']}: matchställ bekräftade", entity_id=team_id, actor=role_label)
            else:
                st.warning("Matchställen ändrades av någon annan och bekräftades därför inte. Senaste version laddas om.")
            st.rerun()

        st.subheader("Mina matcher")
        matches = sorted(
            team_matches,
            key=lambda row: (
                str(row["scheduled_start"] or ""),
                int(row["pitch_number"] or 0),
                int(row["id"]),
            ),
        )
        if matches:
            for match_row in matches:
                score = ""
                if match_row["home_score"] is not None and match_row["away_score"] is not None:
                    score = f" · {match_row['home_score']}–{match_row['away_score']}"
                st.markdown(f"**{html.escape(deps.portal_match_label(match_row))}{score}**")
        else:
            st.caption("Inga schemalagda matcher ännu.")

        st.subheader("Ansvarig kontaktperson")
        contact_notice_key=f"portal_contact_notice_{team_id}"
        if contact_notice_key in st.session_state:
            notice_type, notice_text = st.session_state.pop(contact_notice_key)
            if notice_type == "success":
                st.success(notice_text)
            else:
                st.warning(notice_text)
        with st.form(f"portal_contact_{team_id}"):
            contact_name = st.text_input("Namn", value=deps.team_value(team_row, "responsible_name", "") or "")
            contact_phone = st.text_input("Telefon", value=deps.team_value(team_row, "responsible_phone", "") or "")
            contact_email = st.text_input("E-post", value=deps.team_value(team_row, "responsible_email", "") or "")
            allow_public = bool(deps.row_value(tournament, "allow_team_public_contact", 0))
            contact_public = st.checkbox(
                "Visa kontaktpersonen publikt",
                value=bool(deps.team_value(team_row, "public_contact_enabled", 0)) and allow_public,
                disabled=not allow_public,
                help="Kontaktuppgifter är interna som standard. Detta val kan bara aktiveras om arrangören tillåter publika lagkontakter.",
            )
            if st.form_submit_button("Spara kontaktuppgifter"):
                public_enabled = int(bool(contact_public) and allow_public)
                saved, contact_reason = deps.save_team_contact_if_unchanged(
                    team_id,
                    deps.team_contact_snapshot(team_row),
                    contact_name=contact_name,
                    contact_phone=contact_phone,
                    contact_email=contact_email,
                    public_enabled=public_enabled,
                )
                if saved:
                    st.session_state[contact_notice_key]=(
                        "success",
                        "Kontaktuppgifterna är sparade.",
                    )
                    st.rerun()
                elif contact_reason == "invalid_email":
                    st.error("Ange en giltig e-postadress eller lämna fältet tomt.")
                else:
                    st.session_state[contact_notice_key]=(
                        "warning",
                        "Kontaktuppgifterna ändrades av någon annan och dina äldre uppgifter skrevs inte över. Senaste uppgifter har laddats.",
                    )
                    st.rerun()

    with portal_tabs[1]:
        st.subheader("Hantera truppen")
        max_roster = int(deps.row_value(tournament, "max_roster_size", 0) or 0)
        st.caption(f"{len(players)} registrerade spelare" + (f" · max {max_roster}" if max_roster else " · ingen maxgräns satt"))
        with st.form(f"portal_add_player_{team_id}", clear_on_submit=True):
            pc1, pc2 = st.columns(2)
            pfirst = pc1.text_input("Förnamn")
            plast = pc2.text_input("Efternamn")
            pc3, pc4, pc5 = st.columns(3)
            pnumber = pc3.number_input("Nummer", 0, 999, 0)
            current_year = datetime.now().year
            pbirth = pc4.number_input("Födelseår", 1900, current_year, current_year - 12)
            pposition = pc5.text_input("Position/roll", placeholder="Frivilligt")
            pprotected = st.checkbox("Skyddad spelare – visa inte namn publikt", value=False)
            if st.form_submit_button("Lägg till spelare", type="primary", disabled=bool(max_roster and len(players) >= max_roster)):
                if not pfirst.strip() or not plast.strip():
                    st.error("Ange både förnamn och efternamn.")
                elif max_roster and len(players) >= max_roster:
                    st.error(f"Arrangören har satt max {max_roster} spelare.")
                else:
                    full_name = f"{pfirst.strip()} {plast.strip()}"
                    added, add_reason = deps.add_team_player_if_capacity(
                        team_id,
                        max_roster,
                        player_number=pnumber,
                        name=full_name,
                        first_name=pfirst.strip(),
                        last_name=plast.strip(),
                        birth_year=int(pbirth),
                        position=pposition.strip(),
                        is_protected=pprotected,
                    )
                    if added:
                        deps.record_audit(tournament_id, "roster_player_added", "team", f"{team_row['name']}: {full_name} tillagd", entity_id=team_id, actor=role_label)
                    elif add_reason == "roster_full":
                        st.warning(f"Truppen har redan nått maxgränsen på {max_roster} spelare. Ingen spelare lades till.")
                    st.rerun()
        for player in players:
            with st.expander(f"#{player['player_number'] if player['player_number'] is not None else '–'} {deps.player_display_name(player)}"):
                with st.form(f"portal_edit_player_{player['id']}"):
                    ec1, ec2 = st.columns(2)
                    legacy_parts = str(player["name"] or "").strip().split(" ", 1)
                    default_first = deps.row_value(player, "first_name", "") or (legacy_parts[0] if legacy_parts else "")
                    default_last = deps.row_value(player, "last_name", "") or (legacy_parts[1] if len(legacy_parts) > 1 else "")
                    efirst = ec1.text_input("Förnamn", value=default_first)
                    elast = ec2.text_input("Efternamn", value=default_last)
                    ec3, ec4, ec5 = st.columns(3)
                    enumber = ec3.number_input("Nummer", 0, 999, int(player["player_number"] or 0))
                    ebirth = ec4.number_input("Födelseår", 1900, datetime.now().year, int(deps.row_value(player, "birth_year", datetime.now().year - 12) or datetime.now().year - 12))
                    eposition = ec5.text_input("Position/roll", value=player["position"] or "")
                    eprotected = st.checkbox("Skyddad spelare – visa inte namn publikt", value=bool(deps.row_value(player, "is_protected", 0)))
                    save_player = st.form_submit_button("Spara")
                player_expected = deps.player_snapshot(player)
                if save_player:
                    if not efirst.strip() or not elast.strip():
                        st.error("Ange både förnamn och efternamn.")
                    else:
                        full_name = f"{efirst.strip()} {elast.strip()}"
                        saved, save_reason = deps.update_team_player_if_unchanged(
                            player["id"],
                            team_id,
                            player_expected,
                            player_number=enumber,
                            name=full_name,
                            first_name=efirst.strip(),
                            last_name=elast.strip(),
                            birth_year=int(ebirth),
                            position=eposition.strip(),
                            is_protected=eprotected,
                        )
                        if not saved and save_reason == "conflict":
                            st.warning("Spelaren ändrades av någon annan och dina äldre uppgifter skrevs inte över.")
                        st.rerun()
                if st.button("Ta bort spelaren", key=f"portal_delete_player_{player['id']}"):
                    deleted, delete_reason = deps.delete_team_player_if_unchanged(
                        player["id"],
                        team_id,
                        player_expected,
                    )
                    if deleted:
                        deps.record_audit(tournament_id, "roster_player_deleted", "team", f"{team_row['name']}: spelare borttagen", entity_id=team_id, actor=role_label)
                    elif delete_reason == "conflict":
                        st.warning("Spelaren ändrades av någon annan och raderades därför inte. Senaste uppgifter laddas om.")
                    st.rerun()

    with portal_tabs[2]:
        st.subheader("Matchtrupper")
        deadline_minutes = int(deps.row_value(tournament, "squad_deadline_minutes", 30) or 0)
        st.caption(f"Matchtruppen låses {deadline_minutes} minuter före matchstart. Admin kan alltid ändra den.")
        if not team_matches:
            st.info("Inga matcher att registrera matchtrupp för ännu.")
        else:
            team_match_by_id = {int(row["id"]): row for row in team_matches}
            roster_ids_by_match = {}
            for roster_row in roster_rows:
                roster_ids_by_match.setdefault(int(roster_row["match_id"]), []).append(int(roster_row["player_id"]))
            rostered_match_ids = set(roster_ids_by_match)

            match_id = st.selectbox(
                "Välj match",
                list(team_match_by_id),
                format_func=lambda mid: deps.portal_match_label(team_match_by_id[int(mid)]),
                key=f"portal_squad_match_{team_id}",
            )
            match_row = team_match_by_id[int(match_id)]
            locked = squad_is_locked(match_row["scheduled_start"], deadline_minutes)
            deadline = squad_deadline_at(match_row["scheduled_start"], deadline_minutes)
            if locked:
                st.warning(f"Matchtruppen är låst. Deadline var {deps.swedish_datetime(deadline.isoformat(timespec='minutes'))}.")
            else:
                st.info(f"Deadline: {deps.swedish_datetime(deadline.isoformat(timespec='minutes')) if deadline else 'Ingen deadline'}")
            # `players` was already loaded for the Trupp tab earlier in this render.
            existing_ids = set(roster_ids_by_match.get(int(match_id), []))
            options = [int(row["id"]) for row in players]
            player_label_by_id = {
                int(row["id"]): f"#{row['player_number'] if row['player_number'] is not None else '–'} {row['name']}"
                for row in players
            }
            selected_ids = st.multiselect(
                "Spelare i matchtruppen",
                options,
                default=[pid for pid in options if pid in existing_ids],
                format_func=lambda pid: player_label_by_id[int(pid)],
                disabled=locked,
                key=f"portal_match_roster_{match_id}_{team_id}",
            )
            prev_with_roster = next(
                (
                    candidate
                    for candidate in reversed([row for row in team_matches if row["scheduled_start"] < match_row["scheduled_start"]])
                    if int(candidate["id"]) in rostered_match_ids
                ),
                None,
            )
            bc1, bc2 = st.columns(2)
            if bc1.button("Spara matchtrupp", type="primary", disabled=locked, key=f"save_match_roster_{match_id}_{team_id}", use_container_width=True):
                saved, save_reason = deps.save_match_roster_if_unchanged(
                    match_id,
                    team_id,
                    selected_ids,
                    existing_ids,
                    role_label,
                )
                if saved:
                    deps.record_audit(tournament_id, "match_roster_saved", "match", f"{team_row['name']}: matchtrupp sparad ({len(selected_ids)} spelare)", entity_id=match_id, actor=role_label)
                    st.success("Matchtruppen är sparad.")
                elif save_reason == "conflict":
                    st.warning("Matchtruppen ändrades av någon annan och skrevs inte över. Senaste truppen laddas om.")
                else:
                    st.error("Matchtruppen kunde inte sparas eftersom en vald spelare inte längre tillhör laget.")
                st.rerun()
            if bc2.button("Kopiera föregående matchtrupp", disabled=locked or prev_with_roster is None, key=f"copy_match_roster_{match_id}_{team_id}", use_container_width=True):
                previous_ids = list(roster_ids_by_match.get(int(prev_with_roster["id"]), []))
                valid_ids = {int(row["id"]) for row in players}
                copied_ids = [pid for pid in previous_ids if int(pid) in valid_ids]
                saved, save_reason = deps.save_match_roster_if_unchanged(
                    match_id,
                    team_id,
                    copied_ids,
                    existing_ids,
                    role_label,
                )
                if saved:
                    st.success("Föregående matchtrupp kopierades.")
                elif save_reason == "conflict":
                    st.warning("Matchtruppen ändrades av någon annan och skrevs inte över. Senaste truppen laddas om.")
                else:
                    st.error("Matchtruppen kunde inte kopieras eftersom spelartruppen ändrades.")
                st.rerun()
            if not existing_ids:
                st.warning("⚠️ Matchtrupp ej registrerad.")

    with portal_tabs[3]:
        st.subheader("Meddelanden")
        st.caption("Skriv internt till arrangören eller till ett annat deltagande lag i samma cup. Meddelanden visas bara för berörda parter och arrangören.")
        team_names = {int(row["id"]): row["name"] for row in teams}
        recipients = [("organizer", None, "Arrangören")] + [
            ("team", int(row["id"]), row["name"]) for row in teams if int(row["id"]) != team_id
        ]
        portal_message_token_key=f"portal_message_request_token_{team_id}"
        if portal_message_token_key not in st.session_state:
            st.session_state[portal_message_token_key]=new_token()
        with st.form(f"portal_send_message_{team_id}", clear_on_submit=True):
            recipient_index = st.selectbox(
                "Till",
                range(len(recipients)),
                format_func=lambda idx: recipients[idx][2],
                key=f"portal_message_recipient_{team_id}",
            )
            msg_subject = st.text_input("Ämne", placeholder="Exempel: Förfrågan om träningsmatch", max_chars=200)
            msg_body = st.text_area(
                "Meddelande",
                placeholder="Exempel: Hej! Vi möts i cupen och skulle gärna spela en träningsmatch mot er senare under säsongen.",
                max_chars=3000,
                height=120,
            )
            send_message = st.form_submit_button("Skicka meddelande", type="primary", use_container_width=True)
        if send_message:
            recipient_type, recipient_team_id, _ = recipients[int(recipient_index)]
            try:
                deps.send_team_message(
                    tournament_id,
                    "team",
                    msg_subject,
                    msg_body,
                    sender_team_id=team_id,
                    recipient_type=recipient_type,
                    recipient_team_id=recipient_team_id,
                    request_token=st.session_state[portal_message_token_key],
                )
                st.session_state.pop(portal_message_token_key,None)
                deps.record_audit(tournament_id, "team_message_sent", "team", f"{team_row['name']}: meddelande skickat", entity_id=team_id, actor=role_label)
                st.success("Meddelandet är skickat.")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))

        inbox, sent = st.tabs(["Inkorg", "Skickat"])
        with inbox:
            unread_ids = [int(row["id"]) for row in received_messages if not row["read_at"]]
            if unread_ids and st.button(
                f"Markera alla som lästa ({len(unread_ids)})",
                key=f"portal_mark_messages_read_{team_id}",
            ):
                deps.mark_team_messages_read(
                    unread_ids,
                    tournament_id=tournament_id,
                    recipient_type="team",
                    recipient_team_id=team_id,
                )
                st.rerun()
            if not received_messages:
                st.info("Inga mottagna meddelanden ännu.")
            for msg in received_messages:
                sender, _ = deps.message_party_label(msg, team_names)
                with st.container(border=True):
                    unread_prefix = "🔴 " if not msg["read_at"] else ""
                    st.markdown(f"**{unread_prefix}{html.escape(msg['subject'])}**")
                    st.caption(f"Från {html.escape(sender)} · {msg['created_at']}")
                    st.write(msg["message"])

        with sent:
            sent_messages = fetch_sent_messages(deps.all_rows, tournament_id, team_id)
            if not sent_messages:
                st.info("Inga skickade meddelanden ännu.")
            for msg in sent_messages:
                _, recipient = deps.message_party_label(msg, team_names)
                with st.container(border=True):
                    st.markdown(f"**{html.escape(msg['subject'])}**")
                    st.caption(f"Till {html.escape(recipient)} · {msg['created_at']}")
                    email_status=str(deps.row_value(msg,"email_status","") or "")
                    if msg["recipient_type"] == "team":
                        email_status_label={
                            "sent":"E-postnotis skickad",
                            "failed":"E-postnotis kunde inte skickas",
                            "skipped":"Ingen e-postadress registrerad",
                            "pending":"E-postnotis behandlas",
                        }.get(email_status,"")
                        if email_status_label:
                            st.caption(email_status_label)
                    st.write(msg["message"])
