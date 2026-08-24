import sqlite3
import html
import base64
import hmac
import json
import os
import random
import re
import io
import time
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlencode, quote, urlparse
from urllib.request import Request, urlopen

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from cupnavi_core.version import APP_VERSION as CORE_APP_VERSION
from cupnavi_core.rules import validate_match_event_totals
from cupnavi_core.home_away import orientation_balance_score
from cupnavi_core.pdf_export import build_schedule_pdf
from cupnavi_core.migrations import apply_migrations, LATEST_SCHEMA_VERSION
from cupnavi_core.health import collect_database_health
from cupnavi_core.backup import build_backup_bytes
from cupnavi_core.config import BACKUP_FILE_SUFFIX, PUBLIC_BASE_URL, OFFICIAL_PUBLIC_BASE_URL, LEGACY_STREAMLIT_BASE_URL
from cupnavi_core.schedule_repository import ScheduleRepository
from cupnavi_core.schedule_domain import build_schedule_window, schedule_source_team_id
from cupnavi_core.import_service import (
    TEAM_FIELDS, PLAYER_FIELDS, auto_map_columns,
    build_team_import_plan, build_player_import_plan,
)
from cupnavi_core.team_portal import generate_access_code, new_code_hash, verify_access_code, squad_deadline_at, squad_is_locked
from cupnavi_core.experience import (
    SPORT_PROFILES, sport_profile, match_duration_minutes, analyze_schedule_change,
    planned_delay_updates, tournament_quality_score, playoff_preview, cup_summary,
)
from cupnavi_core.sports import sport_definition
from cupnavi_core.match_engine import match_format, score_model
from cupnavi_core.schedule_optimizer import optimize_match_order, ortools_available
from cupnavi_core.i18n import SUPPORTED_LOCALES, DEFAULT_LOCALE, DEFAULT_TIMEZONE, valid_timezone
from cupnavi_core.lifecycle import normalize_status, status_label, is_public_status, is_editable_status, choose_unique_slug
from cupnavi_core.qol import TOURNAMENT_TEMPLATES, template_definition, clone_tournament_payload, checklist_items, admin_mode

APP_BUILD_VERSION = "2026.08.24-106-TEAM-PRIVACY"
APP_VERSION = APP_BUILD_VERSION
RELEASE_FILES_MISMATCH = CORE_APP_VERSION != APP_BUILD_VERSION
REQUIRED_SCHEMA_VERSION = max(int(LATEST_SCHEMA_VERSION), 5)

try:
    from streamlit_sortables import sort_items
except ImportError:
    sort_items = None

try:
    import qrcode
except ImportError:
    qrcode = None



PUBLIC_APP_URL = PUBLIC_BASE_URL.rstrip("/") + "/"


def public_cup_url(tournament_id):
    """Permanent public link. Slug is preferred; numeric IDs remain backward compatible."""
    row = one_row("SELECT public_slug FROM tournaments WHERE id=?", (int(tournament_id),))
    public_key = row["public_slug"] if row and row["public_slug"] else str(int(tournament_id))
    return f"{PUBLIC_APP_URL}?cup={quote(str(public_key))}"


def share_panel_html(tournament_id, tournament_name):
    """Enkel delning via operativsystemets delningsmeny."""
    share_url = public_cup_url(tournament_id)
    english = current_language() == "en"

    message = (
        f"Follow {tournament_name} in CupNavi: {share_url}"
        if english
        else f"Följ {tournament_name} i CupNavi: {share_url}"
    )
    title = "Share tournament" if english else "Dela cupen"
    button_label = "Share tournament" if english else "Dela cupen"
    help_text = (
        "Choose Messenger, WhatsApp, SMS, email or another app in your device's share menu."
        if english else
        "Välj Messenger, WhatsApp, SMS, e-post eller en annan app i enhetens delningsmeny."
    )
    copied_text = (
        "The link was copied because your browser does not support the share menu."
        if english else
        "Länken kopierades eftersom webbläsaren inte stöder delningsmenyn."
    )
    manual_text = (
        "Copy the link below and share it in the app you want."
        if english else
        "Kopiera länken nedan och dela den i den app du vill använda."
    )

    return f"""
    <style>
      body {{ margin:0; font-family:Arial,sans-serif; color:#172033; }}
      .share-card {{
        border:1px solid #d7dee5;
        border-radius:14px;
        background:#fff;
        padding:14px 16px;
      }}
      .share-title {{
        font-size:16px;
        font-weight:800;
      }}
      .share-help {{
        font-size:13px;
        color:#64748b;
        margin-top:4px;
      }}
      .share-button {{
        width:100%;
        min-height:46px;
        margin-top:12px;
        border:1px solid #bfdbfe;
        border-radius:10px;
        background:#eef4ff;
        color:#1d4ed8;
        font-size:15px;
        font-weight:800;
        cursor:pointer;
      }}
      .share-button:focus-visible {{
        outline:3px solid rgba(37,99,235,.35);
        outline-offset:2px;
      }}
      .share-status {{
        font-size:12px;
        color:#64748b;
        margin-top:9px;
      }}
      .share-url {{
        font-size:11px;
        color:#94a3b8;
        margin-top:7px;
        overflow-wrap:anywhere;
      }}
    </style>

    <div class="share-card">
      <div class="share-title">📤 {html.escape(title)}</div>
      <div class="share-help">{html.escape(help_text)}</div>
      <button id="nativeShare" class="share-button">📤 {html.escape(button_label)}</button>
      <div id="shareStatus" class="share-status"></div>
      <div class="share-url">{html.escape(share_url)}</div>
    </div>

    <script>
      const button = document.getElementById("nativeShare");
      const status = document.getElementById("shareStatus");

      const shareData = {{
        title: {json.dumps("CupNavi – " + tournament_name)},
        text: {json.dumps(message)},
        url: {json.dumps(share_url)}
      }};

      button.addEventListener("click", async () => {{
        if (navigator.share) {{
          try {{
            await navigator.share(shareData);
          }} catch (err) {{
            if (err && err.name !== "AbortError") {{
              status.textContent = {json.dumps(manual_text)};
            }}
          }}
        }} else {{
          try {{
            await navigator.clipboard.writeText(shareData.url);
            status.textContent = {json.dumps(copied_text)};
          }} catch (err) {{
            status.textContent = {json.dumps(manual_text)};
          }}
        }}
      }});
    </script>
    """



def render_share_panel(tournament_id, tournament_name):
    components.html(share_panel_html(tournament_id, tournament_name), height=180, scrolling=False)


def qr_share_panel_html(tournament_id, tournament_name):
    """Visa QR-kod och dela själva PNG-filen via Web Share där det stöds."""
    qr_bytes = qr_png_bytes(public_cup_url(tournament_id))
    if not qr_bytes:
        return None

    english = current_language() == "en"
    encoded_png = base64.b64encode(qr_bytes).decode("ascii")
    title = "QR code" if english else "QR-kod"
    share_label = "Share QR code" if english else "Dela QR-kod"
    download_label = "Download QR code" if english else "Ladda ner QR-kod"
    help_text = (
        "Share the QR image itself, or download it for printing."
        if english else
        "Dela själva QR-bilden eller ladda ner den för utskrift."
    )
    fallback_text = (
        "Your browser cannot share image files directly. The QR code has been downloaded instead."
        if english else
        "Din webbläsare kan inte dela bildfiler direkt. QR-koden laddas ner i stället."
    )
    filename = f"cupnavi_qr_{int(tournament_id)}.png"

    return f"""
    <style>
      body {{ margin:0; font-family:Arial,sans-serif; color:#172033; }}
      .qr-card {{
        display:grid;
        grid-template-columns:180px 1fr;
        gap:18px;
        align-items:center;
        border:1px solid #d7dee5;
        border-radius:14px;
        background:#fff;
        padding:14px 16px;
      }}
      .qr-image {{
        width:170px;
        height:170px;
        object-fit:contain;
        border:1px solid #e2e8f0;
        border-radius:10px;
        background:#fff;
      }}
      .qr-title {{font-size:16px;font-weight:800}}
      .qr-help {{font-size:13px;color:#64748b;margin-top:4px}}
      .qr-actions {{
        display:flex;
        gap:8px;
        flex-wrap:wrap;
        margin-top:12px;
      }}
      .qr-button {{
        flex:1 1 180px;
        min-height:44px;
        border-radius:10px;
        border:1px solid #cbd5e1;
        font-size:14px;
        font-weight:800;
        cursor:pointer;
        text-decoration:none;
        display:flex;
        align-items:center;
        justify-content:center;
        box-sizing:border-box;
      }}
      .share {{background:#eef4ff;color:#1d4ed8;border-color:#bfdbfe}}
      .download {{background:#f8fafc;color:#334155}}
      .qr-status {{font-size:12px;color:#64748b;margin-top:9px}}
      @media(max-width:520px) {{
        .qr-card {{grid-template-columns:1fr;text-align:center}}
        .qr-image {{margin:0 auto}}
      }}
    </style>

    <div class="qr-card">
      <img class="qr-image" src="data:image/png;base64,{encoded_png}" alt="{html.escape(title)}">
      <div>
        <div class="qr-title">▣ {html.escape(title)}</div>
        <div class="qr-help">{html.escape(help_text)}</div>
        <div class="qr-actions">
          <button id="shareQr" class="qr-button share">📤 {html.escape(share_label)}</button>
          <a class="qr-button download"
             href="data:image/png;base64,{encoded_png}"
             download="{html.escape(filename, quote=True)}">⬇️ {html.escape(download_label)}</a>
        </div>
        <div id="qrStatus" class="qr-status"></div>
      </div>
    </div>

    <script>
      const shareButton = document.getElementById("shareQr");
      const status = document.getElementById("qrStatus");
      const base64Data = {json.dumps(encoded_png)};
      const filename = {json.dumps(filename)};
      const mimeType = "image/png";

      function base64ToBlob(base64, type) {{
        const binary = atob(base64);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) {{
          bytes[i] = binary.charCodeAt(i);
        }}
        return new Blob([bytes], {{type}});
      }}

      shareButton.addEventListener("click", async () => {{
        const blob = base64ToBlob(base64Data, mimeType);
        const file = new File([blob], filename, {{type: mimeType}});

        if (navigator.share && navigator.canShare && navigator.canShare({{files:[file]}})) {{
          try {{
            await navigator.share({{
              title: {json.dumps("CupNavi – " + tournament_name)},
              text: {json.dumps("QR code for " + tournament_name)},
              files: [file]
            }});
            return;
          }} catch (err) {{
            if (err && err.name === "AbortError") return;
          }}
        }}

        const link = document.createElement("a");
        link.href = URL.createObjectURL(blob);
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        link.remove();
        setTimeout(() => URL.revokeObjectURL(link.href), 1000);
        status.textContent = {json.dumps(fallback_text)};
      }});
    </script>
    """


def render_qr_share_panel(tournament_id, tournament_name):
    qr_html = qr_share_panel_html(tournament_id, tournament_name)
    if qr_html:
        components.html(qr_html, height=240, scrolling=False)



def _visitor_header(name):
    """Läs en HTTP-header om Streamlit exponerar den, annars tom sträng."""
    try:
        headers = st.context.headers
        return str(headers.get(name, "") or headers.get(name.lower(), "") or "").strip()
    except Exception:
        return ""


def _visitor_device_type(user_agent):
    ua = (user_agent or "").lower()
    if any(token in ua for token in ("ipad", "tablet")):
        return "Surfplatta"
    if any(token in ua for token in ("mobi", "iphone", "android")):
        return "Mobil"
    return "Dator"


def _visitor_browser(user_agent):
    ua = (user_agent or "").lower()
    if "edg/" in ua:
        return "Edge"
    if "opr/" in ua or "opera" in ua:
        return "Opera"
    if "chrome/" in ua and "edg/" not in ua:
        return "Chrome"
    if "safari/" in ua and "chrome/" not in ua:
        return "Safari"
    if "firefox/" in ua:
        return "Firefox"
    return "Övrig"


def _visitor_source(referrer):
    ref = (referrer or "").lower()
    if not ref:
        return "Direkt / okänd"
    if "google." in ref:
        return "Google"
    if "facebook." in ref or "messenger." in ref or "l.facebook." in ref:
        return "Facebook / Messenger"
    if "whatsapp." in ref:
        return "WhatsApp"
    if "instagram." in ref:
        return "Instagram"
    return "Annan webbplats"


def track_public_visit(tournament_id):
    """Integritetsvänlig besöksmätning. Ingen IP-adress eller personuppgift lagras."""
    session_key = f"_cupnavi_visitor_session_{tournament_id}"
    token = st.session_state.get(session_key)
    if not token:
        token = hashlib.sha256(os.urandom(32)).hexdigest()
        st.session_state[session_key] = token

    now_dt = datetime.now()
    now_iso = now_dt.isoformat(timespec="seconds")
    throttle_key = f"_cupnavi_visit_last_count_{tournament_id}"
    previous_count_at = st.session_state.get(throttle_key)
    count_view = (
        previous_count_at is None
        or (now_dt - previous_count_at).total_seconds() >= 60
    )
    if not count_view:
        return

    user_agent = _visitor_header("User-Agent")
    referrer = _visitor_header("Referer")
    device_type = _visitor_device_type(user_agent)
    browser = _visitor_browser(user_agent)
    source = _visitor_source(referrer)

    existing = one_row(
        """SELECT id,view_count FROM visitor_sessions
           WHERE tournament_id=? AND session_token=?""",
        (tournament_id, token),
    )
    if existing:
        run(
            """UPDATE visitor_sessions
               SET last_seen=?,view_count=view_count+1,device_type=?,browser=?,source=?
               WHERE id=?""",
            (now_iso, device_type, browser, source, existing["id"]),
        )
        st.session_state[throttle_key] = now_dt
    else:
        run(
            """INSERT INTO visitor_sessions(
                   tournament_id,session_token,first_seen,last_seen,view_count,
                   device_type,browser,source
               ) VALUES(?,?,?,?,1,?,?,?)""",
            (tournament_id, token, now_iso, now_iso, device_type, browser, source),
        )
        st.session_state[throttle_key] = now_dt


@st.cache_data(show_spinner=False)
def qr_png_bytes(value):
    """QR-bilden är deterministisk och behöver inte byggas om vid varje rerun."""
    if qrcode is None:
        return None
    image = qrcode.make(value)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def normalize_website_url(value):
    """Normalisera en frivillig webbplatsadress och validera utan regex."""
    value = str(value or "").strip()
    if not value:
        return None

    # Gör det enklare för arrangören: example.se blir https://example.se
    candidate = value if "://" in value else f"https://{value}"
    parsed = urlparse(candidate)

    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(
            "Webbplatsen verkar inte vara giltig. Ange till exempel https://example.se."
        )

    # Undvik blanksteg/control chars i hostnamn.
    if any(ch.isspace() for ch in parsed.netloc):
        raise ValueError(
            "Webbplatsen verkar inte vara giltig. Ange till exempel https://example.se."
        )
    return candidate


def image_data_uri(uploaded_file):
    """Konvertera en liten uppladdad sponsorlogga till en portabel data-URI."""
    if uploaded_file is None:
        return None
    raw = uploaded_file.getvalue()
    if len(raw) > 1_500_000:
        raise ValueError("Logotypen får vara högst 1,5 MB.")
    mime = uploaded_file.type or "image/png"
    if mime not in {"image/png", "image/jpeg", "image/webp"}:
        raise ValueError("Logotypen måste vara PNG, JPG eller WEBP.")
    return f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"



TRANSLATIONS = {
    "sv": {},
    "en": {
        "Välj språk": "Choose language", "Turneringar": "Tournaments",
        "Välj läge": "Choose mode", "Turneringsvy": "Tournament view",
        "Matchrapportör": "Match reporter", "Visningsläge": "Mode",
        "Aktiv turnering": "Active tournament", "Instruktioner": "Instructions",
        "Översikt": "Overview", "Kontroller": "Checks", "Lag": "Teams",
        "Grupper": "Groups", "Trupper": "Squads", "Domare": "Referees",
        "Schema": "Schedule", "Tabeller": "Standings", "Matcher": "Matches",
        "Händelser": "Events", "Slutspel": "Playoffs", "Skytteligor": "Leaderboards",
        "Erbjudanden": "Offers", "Sponsorer": "Sponsors", "Funktionärer": "Staff",
        "Import": "Import", "Besök": "Visitors", "Besöksstatistik": "Visitor analytics",
        "Spelschema": "Schedule", "Resultat": "Results", "Topplistor": "Statistics",
        "Partners": "Partners", "Information": "Information", "Alla matcher": "All matches",
        "En grupp": "A group", "Ett lag": "A team", "En plan": "A pitch",
        "Vad vill du visa?": "What do you want to show?", "Välj grupp": "Choose group",
        "Välj lag": "Choose team", "Alla lag": "All teams", "Visa alla lag": "Show all teams", "Välj plan": "Choose pitch", "Plan": "Pitch",
        "Skytteliga": "Top scorers", "Assistliga": "Assists",
        "Varningar och utvisningar": "Cards", "Praktisk information": "Practical information",
        "Cupens partners": "Tournament partners",
        "Erbjudanden för cupdeltagare": "Offers for tournament participants",
        "Matchhändelser": "Match events", "Arena": "Venue", "Kiosk": "Refreshments",
        "Kontakta arrangören": "Contact the organizer",
        "Frågor eller feedback": "Questions or feedback", "Följ cupen": "Follow the tournament",
        "Lösenord": "Password", "Adminlösenord": "Admin password",
        "Logga in": "Sign in", "Logga ut": "Sign out", "Fel lösenord.": "Incorrect password.",
        "Inloggad som administratör": "Signed in as administrator",
        "Inloggad som matchrapportör": "Signed in as match reporter",
        "Administratörsinloggning": "Administrator sign-in",
        "Administration": "Administration", "Period": "Period",
        "Senaste 7 dagarna": "Last 7 days", "Senaste 30 dagarna": "Last 30 days",
        "Senaste 90 dagarna": "Last 90 days", "All tid": "All time",
        "Unika sessioner": "Unique sessions", "Sidvisningar": "Page views",
        "Besök idag": "Visits today", "Sidvisningar idag": "Page views today",
        "Aktiva senaste 30 min": "Active in last 30 min", "Utveckling över tid": "Trend over time",
        "Enheter": "Devices", "Webbläsare": "Browsers", "Trafikkälla": "Traffic source",
        "Senaste besöken": "Recent visits", "Mobil": "Mobile", "Dator": "Desktop",
        "Surfplatta": "Tablet", "Direkt / okänd": "Direct / unknown",
        "Skapa": "Create", "Spara": "Save", "Avbryt": "Cancel", "Publicera": "Publish",
        "Avpublicera": "Unpublish", "Namn": "Name", "Namn *": "Name *", "Telefon": "Phone",
        "E-post": "Email", "Webbplats": "Website", "Rubrik": "Title", "Rubrik *": "Title *",
        "Beskrivning / villkor": "Description / terms", "Kort beskrivning": "Short description",
        "Visningsordning": "Display order", "Grupp": "Group", "Gruppnamn": "Group name",
        "Lagnamn": "Team name", "Spelare": "Player", "Tröjnummer": "Shirt number",
        "Födelseår": "Birth year", "Position": "Position", "Roll": "Role", "Roll *": "Role *",
        "Datum": "Date", "Avspark": "Kick-off", "Antal planer": "Number of pitches",
        "Första matchstart": "First kick-off", "Spelort": "Location",
        "Turneringens namn": "Tournament name", "Planerat antal lag": "Planned number of teams",
        "Första cupdag": "First tournament day", "Sista cupdag": "Last tournament day",
        "Arenaadress": "Venue address", "Arrangörens telefonnummer": "Organizer phone number",
        "E-post för feedback": "Feedback email", "Övrig information": "Other information",
        "Mål": "Goals", "Assist": "Assists", "Varningar": "Yellow cards",
        "Utvisningar": "Red cards", "Match": "Match", "Fas": "Stage",
        "Hemmalag": "Home team", "Bortalag": "Away team", "Hemmamål": "Home goals",
        "Bortamål": "Away goals", "Publicerad": "Published", "Publicerade": "Published",
        "Ej publicerade": "Unpublished", "Schemalagda": "Scheduled",
        "Schemalagda matcher": "Scheduled matches", "Gruppspelsmatcher": "Group-stage matches",
        "CupNavi Score": "CupNavi Score", "Domarcentral": "Referee centre",
        "Offlineutkast": "Offline draft", "Cupverktyg": "Tournament tools",
        "Cupflöde": "Tournament feed", "Cupkarta": "Tournament map",
        "Kvalitet": "Quality", "Försening": "Delay", "Historik": "History",
        "Summering": "Summary", "Sport": "Sport",
    }
}

EN_PHRASES = {
    "Skapa och publicera schema": "Create and publish schedule",
    "Matcher och resultat": "Matches and results",
    "Registrera resultat och domare": "Enter results and referees",
    "Registrera mål, assist, varningar och utvisningar": "Enter goals, assists, yellow cards and red cards",
    "Dela cupen med QR-kod": "Share tournament with QR code",
    "Lägg till": "Add", "Ta bort": "Delete", "Redigera": "Edit",
    "Spara ändringar": "Save changes", "Spara alla": "Save all", "Ladda ner": "Download",
    "Välj turnering": "Choose tournament", "Välj match": "Choose match",
    "Välj och spara": "Choose and save", "Ange ett": "Enter a", "Ange en": "Enter a",
    "Ange": "Enter", "Det finns ännu inga": "There are no", "Det finns ännu ingen": "There is no",
    "Det finns inga": "There are no", "Det finns ingen": "There is no",
    "Här visas": "This page shows", "Här kan du": "Here you can",
    "Här ställer du in": "Here you configure", "Här granskar du": "Here you review",
    "Klicka på": "Click", "Gå till": "Go to", "under fliken": "under the tab",
    "i den publika turneringsvyn": "in the public tournament view",
    "i turneringsvyn": "in the tournament view", "den publika turneringsvyn": "the public tournament view",
    "spelschemat": "the schedule", "schemat": "the schedule", "turneringen": "the tournament",
    "gruppen": "the group", "laget": "the team", "matchen": "the match", "spelaren": "the player",
    "domaren": "the referee", "publikt": "publicly", "automatiskt": "automatically",
    "manuellt": "manually", "före publicering": "before publishing", "efter publicering": "after publishing",
    "kan inte": "cannot", "måste": "must", "behöver": "needs to", "sparas": "is saved",
    "skapade": "created", "skapats": "been created", "publiceras": "is published",
    "registrerade": "registered", "registreras": "are registered", "uppdateras": "is updated",
    "ändras": "changes", "kontrolleras": "is checked", "visas": "is shown", "saknas": "is missing",
    "resultat": "results", "matchhändelser": "match events", "slutspel": "playoffs",
    "gruppspel": "group stage", "grupper": "groups", "spelare": "players",
    "domare": "referees", "matcher": "matches", "schema": "schedule",
    "turnering": "tournament", "varningar": "warnings", "utvisningar": "red cards",
    "mål": "goals", "assist": "assists", "poäng": "points", "planer": "pitches",
}

EN_WORDS = {
    "och": "and", "eller": "or", "för": "for", "från": "from", "till": "to",
    "med": "with", "utan": "without", "är": "is", "har": "has", "ska": "should",
    "kan": "can", "inte": "not", "alla": "all", "hela": "entire", "vald": "selected",
    "valda": "selected", "aktuell": "current", "aktuella": "current", "ny": "new",
    "nya": "new", "första": "first", "sista": "last", "innan": "before", "efter": "after",
    "ovan": "above", "nedan": "below", "direkt": "directly", "endast": "only",
    "även": "also", "inga": "no", "ingen": "no", "ett": "a", "en": "a",
    "den": "the", "det": "it", "de": "the", "du": "you", "din": "your", "ditt": "your",
}

def current_language():
    return st.session_state.get("language", "sv")

def _translate_english_fallback(value):
    result = str(value)
    for source, target in sorted(EN_PHRASES.items(), key=lambda item: len(item[0]), reverse=True):
        result = re.sub(re.escape(source), target, result, flags=re.IGNORECASE)
    for source, target in EN_WORDS.items():
        result = re.sub(rf"(?<!\w){re.escape(source)}(?!\w)", target, result, flags=re.IGNORECASE)
    return result

def tr(value):
    if value is None or current_language() != "en" or not isinstance(value, str):
        return value
    exact = TRANSLATIONS["en"].get(value)
    if exact is not None:
        return exact
    if value.lstrip().startswith(("http://", "https://", "<style", "<div", "<script")):
        return value
    return _translate_english_fallback(value)

def _translate_dataframe_for_display(dataframe):
    if current_language() != "en" or dataframe is None or not hasattr(dataframe, "rename"):
        return dataframe
    return dataframe.rename(columns={column: tr(column) for column in dataframe.columns})

def _install_streamlit_translation_hooks():
    if getattr(st, "_cupnavi_translation_hooks", False):
        return
    from streamlit.delta_generator import DeltaGenerator

    simple_methods = (
        "title", "header", "subheader", "caption", "info", "warning", "error", "success",
        "button", "download_button", "text_input", "text_area", "checkbox", "number_input",
        "date_input", "time_input", "file_uploader", "form_submit_button", "metric", "expander",
    )
    for method_name in simple_methods:
        original = getattr(DeltaGenerator, method_name, None)
        if original is None:
            continue
        def make_wrapper(original_method):
            def wrapper(self, *args, **kwargs):
                args = list(args)
                if args and isinstance(args[0], str):
                    args[0] = tr(args[0])
                if isinstance(kwargs.get("placeholder"), str):
                    kwargs["placeholder"] = tr(kwargs["placeholder"])
                if isinstance(kwargs.get("help"), str):
                    kwargs["help"] = tr(kwargs["help"])
                return original_method(self, *args, **kwargs)
            return wrapper
        setattr(DeltaGenerator, method_name, make_wrapper(original))

    original_markdown = DeltaGenerator.markdown
    def markdown_wrapper(self, body, *args, **kwargs):
        if isinstance(body, str) and not kwargs.get("unsafe_allow_html"):
            body = tr(body)
        return original_markdown(self, body, *args, **kwargs)
    DeltaGenerator.markdown = markdown_wrapper

    original_tabs = DeltaGenerator.tabs
    def tabs_wrapper(self, tabs, *args, **kwargs):
        if current_language() == "en":
            tabs = [tr(item) if isinstance(item, str) else item for item in tabs]
        return original_tabs(self, tabs, *args, **kwargs)
    DeltaGenerator.tabs = tabs_wrapper

    for method_name in ("selectbox", "radio"):
        original = getattr(DeltaGenerator, method_name)
        def make_option_wrapper(original_method):
            def wrapper(self, label, options, *args, **kwargs):
                label = tr(label) if isinstance(label, str) else label
                existing = kwargs.get("format_func")
                if current_language() == "en":
                    if existing:
                        kwargs["format_func"] = lambda value, f=existing: tr(f(value))
                    else:
                        kwargs["format_func"] = lambda value: tr(value) if isinstance(value, str) else value
                return original_method(self, label, options, *args, **kwargs)
            return wrapper
        setattr(DeltaGenerator, method_name, make_option_wrapper(original))

    original_data_editor = DeltaGenerator.data_editor
    def data_editor_wrapper(self, data, *args, **kwargs):
        if current_language() != "en" or not hasattr(data, "columns"):
            return original_data_editor(self, data, *args, **kwargs)
        rename_map = {column: tr(column) for column in data.columns}
        reverse_map = {value: key for key, value in rename_map.items()}
        display_data = data.rename(columns=rename_map)
        if isinstance(kwargs.get("disabled"), list):
            kwargs["disabled"] = [rename_map.get(x, x) for x in kwargs["disabled"]]
        if isinstance(kwargs.get("column_order"), list):
            kwargs["column_order"] = [rename_map.get(x, x) for x in kwargs["column_order"]]
        if isinstance(kwargs.get("column_config"), dict):
            kwargs["column_config"] = {rename_map.get(k, k): v for k, v in kwargs["column_config"].items()}
        result = original_data_editor(self, display_data, *args, **kwargs)
        return result.rename(columns=reverse_map) if hasattr(result, "rename") else result
    DeltaGenerator.data_editor = data_editor_wrapper

    st._cupnavi_translation_hooks = True


st.set_page_config(page_title="CupNavi", page_icon="🏆", layout="wide")

st.html("""
<style>
/* ===== DIALOGKONTRAST v41 ===== */
div[role="dialog"] {
    background:#0b1220 !important;
    color:#f8fafc !important;
}
div[role="dialog"] h1,
div[role="dialog"] h2,
div[role="dialog"] h3,
div[role="dialog"] p,
div[role="dialog"] span,
div[role="dialog"] label {
    color:#f8fafc !important;
}
div[role="dialog"] [data-testid="stAlert"] {
    background:#3f1d24 !important;
    border:1px solid #fca5a5 !important;
}
div[role="dialog"] [data-testid="stAlert"] *,
div[role="dialog"] [data-testid="stAlert"] p,
div[role="dialog"] [data-testid="stAlert"] span {
    color:#fee2e2 !important;
}
div[role="dialog"] [data-testid="stCaptionContainer"],
div[role="dialog"] .stCaptionContainer {
    color:#cbd5e1 !important;
}
div[role="dialog"] .stButton > button[kind="primary"] {
    background:#15803d !important;
    border-color:#15803d !important;
    color:#ffffff !important;
}
div[role="dialog"] .stButton > button[kind="primary"] * {
    color:#ffffff !important;
}
div[role="dialog"] .stButton > button:not([kind="primary"]) {
    background:#ffffff !important;
    border-color:#cbd5e1 !important;
    color:#0f172a !important;
}
div[role="dialog"] .stButton > button:not([kind="primary"]) * {
    color:#0f172a !important;
}

          /* ===== CUPNAVI DESIGN SYSTEM v46 ===== */
          :root {
            --cn-bg:#F6F8FA;
            --cn-surface:#FFFFFF;
            --cn-ink:#172033;
            --cn-muted:#64748B;
            --cn-border:#D7DEE5;
            --cn-green:#166534;
            --cn-green-soft:#DCFCE7;
            --cn-amber:#B45309;
            --cn-amber-soft:#FEF3C7;
            --cn-red:#B91C1C;
            --cn-blue:#1D4ED8;
            --cn-radius:12px;
          }

          .cn-dashboard-grid {
            display:grid;
            grid-template-columns:repeat(4,minmax(0,1fr));
            gap:12px;
            margin:10px 0 18px;
          }
          .cn-status-card {
            background:var(--cn-surface);
            border:1px solid var(--cn-border);
            border-radius:var(--cn-radius);
            padding:14px 15px;
            min-height:92px;
          }
          .cn-status-card .cn-label {
            color:var(--cn-muted) !important;
            font-size:12px;
            font-weight:750;
            text-transform:uppercase;
            letter-spacing:.03em;
          }
          .cn-status-card .cn-value {
            color:var(--cn-ink) !important;
            font-size:27px;
            line-height:1.1;
            font-weight:850;
            margin-top:6px;
          }
          .cn-status-card .cn-sub {
            color:var(--cn-muted) !important;
            font-size:12px;
            margin-top:7px;
          }

          .cn-workflow {
            display:grid;
            grid-template-columns:repeat(3,minmax(0,1fr));
            gap:10px;
            margin:12px 0 16px;
          }
          .cn-step {
            background:#fff;
            border:1px solid var(--cn-border);
            border-radius:10px;
            padding:11px 13px;
          }
          .cn-step.done {
            background:var(--cn-green-soft);
            border-color:#86EFAC;
          }
          .cn-step.warn {
            background:var(--cn-amber-soft);
            border-color:#FCD34D;
          }
          .cn-step.todo {
            background:#F8FAFC;
          }
          .cn-step .title {
            color:var(--cn-ink) !important;
            font-weight:800;
          }
          .cn-step .meta {
            color:var(--cn-muted) !important;
            margin-top:4px;
            font-size:12px;
          }
          .cn-action-banner {
            background:var(--cn-amber-soft);
            border:1px solid #FCD34D;
            border-radius:12px;
            padding:14px 16px;
            margin:10px 0 14px;
          }
          .cn-action-banner strong { color:#78350F !important; }
          .cn-action-banner span { color:#92400E !important; }

          @media (max-width:900px) {
            .cn-dashboard-grid { grid-template-columns:repeat(2,minmax(0,1fr)); }
            .cn-workflow { grid-template-columns:repeat(2,minmax(0,1fr)); }
          }
          @media (max-width:520px) {
            .cn-dashboard-grid,
            .cn-workflow { grid-template-columns:1fr; }
          }


          /* ===== UI/UX FAS 2 v47 ===== */
          .cn-next-match {
            background:linear-gradient(135deg,#0f172a,#1e3a5f);
            border:1px solid #334155;
            border-radius:14px;
            padding:16px;
            margin:12px 0 16px;
            color:#ffffff;
          }
          .cn-next-match * { color:#ffffff !important; }
          .cn-next-match .eyebrow {
            font-size:11px;
            font-weight:850;
            letter-spacing:.08em;
            text-transform:uppercase;
            opacity:.78;
          }
          .cn-next-match .teams {
            margin-top:7px;
            font-size:23px;
            font-weight:900;
            line-height:1.2;
          }
          .cn-next-match .meta {
            margin-top:8px;
            font-size:13px;
            opacity:.88;
          }

          .cn-admin-match {
            display:grid;
            grid-template-columns:74px minmax(0,1fr) minmax(0,1fr) 150px;
            gap:10px;
            align-items:center;
            background:#ffffff;
            border:1px solid #d7dee5;
            border-radius:11px;
            padding:10px 12px;
            margin:7px 0;
          }
          .cn-admin-match.issue {
            border-left:5px solid #b45309;
            background:#fffbeb;
          }
          .cn-admin-match .number {
            font-weight:900;
            color:#166534 !important;
          }
          .cn-admin-match .team {
            font-weight:800;
            color:#172033 !important;
            overflow-wrap:anywhere;
          }
          .cn-admin-match .meta {
            color:#64748b !important;
            font-size:12px;
          }
          .cn-issue-pill {
            display:inline-block;
            margin:3px 4px 0 0;
            padding:3px 7px;
            border-radius:999px;
            background:#fef3c7;
            border:1px solid #fcd34d;
            color:#92400e !important;
            font-size:11px;
            font-weight:800;
          }

          @media (max-width:700px) {
            .cn-admin-match {
              grid-template-columns:62px 1fr;
            }
            .cn-admin-match .ref-col {
              grid-column:1 / -1;
            }
            .cn-next-match .teams { font-size:20px; }
          }


          /* ===== PUBLIKT SCHEMAFILTER v52 ===== */
          div[data-testid="stRadio"] > div {
            gap:8px;
          }
          div[data-testid="stRadio"] label {
            border:1px solid #cbd5e1;
            border-radius:999px;
            padding:7px 12px;
            background:#ffffff;
          }


          /* ===== PUBLIKA MATCHHÄNDELSER v56 ===== */
          .cn-match-events {
            margin-top:10px;
            padding-top:9px;
            border-top:1px solid #e2e8f0;
          }
          .cn-events-title {
            text-align:center;
            color:#64748b !important;
            font-size:11px;
            font-weight:800;
            text-transform:uppercase;
            letter-spacing:.04em;
            margin-bottom:6px;
          }
          .cn-events-list {
            display:flex;
            justify-content:center;
            flex-wrap:wrap;
            gap:6px;
          }
          .cn-event {
            display:inline-block;
            border-radius:999px;
            padding:4px 8px;
            font-size:12px;
            font-weight:750;
            line-height:1.2;
          }
          .cn-event.cn-goal {
            background:#ecfdf5;
            border:1px solid #86efac;
            color:#166534 !important;
          }
          .cn-event.cn-red {
            background:#fef2f2;
            border:1px solid #fca5a5;
            color:#991b1b !important;
          }


          .cn-event-teams {
            display:grid;
            grid-template-columns:repeat(2,minmax(0,1fr));
            gap:8px;
          }
          .cn-event-team {
            background:#f8fafc;
            border:1px solid #e2e8f0;
            border-radius:9px;
            padding:7px;
            min-width:0;
          }
          .cn-event-team-name {
            text-align:center;
            color:#334155 !important;
            font-size:12px;
            font-weight:900;
            margin-bottom:6px;
            overflow-wrap:anywhere;
          }
          .cn-event-team .cn-events-list {
            justify-content:center;
          }
          @media (max-width:480px) {
            .cn-event-teams { grid-template-columns:1fr 1fr; gap:6px; }
            .cn-event { font-size:11px; padding:4px 6px; }
          }


          .cn-organizer-contact {
            display:flex;
            align-items:center;
            justify-content:space-between;
            gap:12px;
            flex-wrap:wrap;
          }
          .cn-call-button {
            display:inline-block;
            background:#166534;
            color:#ffffff !important;
            text-decoration:none !important;
            font-weight:850;
            border-radius:10px;
            padding:10px 14px;
            white-space:nowrap;
          }
          .cn-call-button:hover { background:#14532d; color:#ffffff !important; }
          @media (max-width:480px) {
            .cn-organizer-contact { align-items:stretch; }
            .cn-call-button { width:100%; text-align:center; box-sizing:border-box; }
          }


          .cn-email-button {
            display:inline-block;
            background:#1e3a8a;
            color:#ffffff !important;
            text-decoration:none !important;
            font-weight:850;
            border-radius:10px;
            padding:10px 14px;
            white-space:nowrap;
          }
          .cn-email-button:hover { background:#172554; color:#ffffff !important; }
          @media (max-width:480px) {
            .cn-email-button { width:100%; text-align:center; box-sizing:border-box; }
          }


          /* v85 import wizard */
          .cn-import-steps {
            display:grid;
            grid-template-columns:repeat(5, minmax(0,1fr));
            gap:8px;
            margin:10px 0 20px 0;
          }
          .cn-import-steps div {
            display:flex;
            align-items:center;
            gap:7px;
            padding:8px 9px;
            border:1px solid #e2e8f0;
            border-radius:10px;
            background:#f8fafc;
            color:#475569;
            font-size:12px;
            min-width:0;
          }
          .cn-import-steps strong {
            display:inline-flex;
            align-items:center;
            justify-content:center;
            min-width:24px;
            height:24px;
            border-radius:999px;
            background:#e0e7ff;
            color:#3730a3;
          }
          @media (max-width:760px) {
            .cn-import-steps { grid-template-columns:1fr; gap:5px; }
            .cn-import-steps div { padding:7px 9px; }
          }

          /* v83 UX polish */
          .cn-admin-nav-group-title {
            margin:14px 0 6px 0;
            font-size:12px;
            font-weight:850;
            letter-spacing:.04em;
            text-transform:uppercase;
            color:#64748b;
          }
          .cn-current-admin-page {
            display:flex;
            align-items:center;
            gap:8px;
            margin:12px 0 2px 0;
            padding:8px 11px;
            border-radius:10px;
            background:#f8fafc;
            border:1px solid #e2e8f0;
            font-size:13px;
            color:#64748b;
          }
          .cn-current-admin-page strong { color:#172033; }
          .cn-admin-status-strip {
            display:flex;
            align-items:center;
            flex-wrap:wrap;
            gap:9px;
            margin:-4px 0 12px 0;
            font-size:13px;
            color:#475569;
          }
          .cn-admin-status-pill {
            display:inline-block;
            padding:4px 9px;
            border-radius:999px;
            background:#ecfdf5;
            border:1px solid #bbf7d0;
            color:#166534;
            font-weight:800;
          }
          div[data-testid="stButton"] > button,
          div[data-testid="stDownloadButton"] > button { min-height:44px; }
          button:focus-visible, a:focus-visible, input:focus-visible,
          textarea:focus-visible, select:focus-visible {
            outline:3px solid rgba(37,99,235,.35) !important;
            outline-offset:2px !important;
          }
          @media (max-width:640px) {
            .cn-current-admin-page { align-items:flex-start; flex-direction:column; gap:2px; }
          }

          .cn-share-card {
            border:1px solid #d7dee5;
            border-radius:14px;
            background:#ffffff;
            padding:14px 16px;
            margin:10px 0 16px 0;
            box-shadow:0 3px 10px rgba(15,23,42,.05);
          }
          .cn-share-title {
            font-size:16px;
            font-weight:850;
            color:#172033;
          }
          .cn-share-subtitle {
            margin-top:2px;
            font-size:13px;
            color:#64748b;
          }
          .cn-share-buttons {
            display:flex;
            flex-wrap:wrap;
            gap:8px;
            margin-top:11px;
          }
          .cn-share-button {
            display:inline-block;
            text-decoration:none !important;
            font-weight:800;
            border-radius:10px;
            padding:9px 13px;
            border:1px solid #cbd5e1;
            color:#172033 !important;
            background:#f8fafc;
          }
          .cn-share-messenger { background:#eef4ff; border-color:#bfdbfe; color:#1d4ed8 !important; }
          .cn-share-whatsapp { background:#f0fdf4; border-color:#bbf7d0; color:#166534 !important; }
          .cn-share-email { background:#eff6ff; border-color:#bfdbfe; color:#1e3a8a !important; }
          .cn-share-sms { background:#f8fafc; border-color:#cbd5e1; color:#334155 !important; }
          .cn-share-url {
            margin-top:10px;
            font-size:11px;
            color:#64748b;
            overflow-wrap:anywhere;
          }
          @media (max-width:480px) {
            .cn-share-buttons { display:grid; grid-template-columns:1fr 1fr; }
            .cn-share-button { text-align:center; box-sizing:border-box; }
          }


          .cn-instagram-button {
            display:inline-block;
            background:#7c3aed;
            color:#ffffff !important;
            text-decoration:none !important;
            font-weight:850;
            border-radius:10px;
            padding:10px 14px;
            white-space:nowrap;
          }
          .cn-instagram-button:hover { background:#6d28d9; color:#ffffff !important; }
          @media (max-width:480px) {
            .cn-instagram-button { width:100%; text-align:center; box-sizing:border-box; }
          }

</style>
""")


# Global arbetsindikator: visas automatiskt medan Streamlit kör om sidan efter interaktion.
st.html("""
<style>
/* Streamlits running-status finns medan Python-skriptet arbetar.
   Förstärk den till en tydlig CupNavi-indikator utan att blockera sidan. */
[data-testid="stStatusWidget"] {
    position: fixed !important;
    top: 12px !important;
    left: 50% !important;
    transform: translateX(-50%) !important;
    z-index: 999999 !important;
    background: #0f172a !important;
    color: #ffffff !important;
    border: 1px solid #334155 !important;
    border-radius: 999px !important;
    padding: 8px 14px !important;
    box-shadow: 0 8px 24px rgba(15,23,42,.22) !important;
}
[data-testid="stStatusWidget"]::after {
    content: "  CupNavi arbetar…";
    color: #ffffff;
    font-weight: 800;
    white-space: nowrap;
}
[data-testid="stSpinner"] {
    font-weight: 800 !important;
}
</style>
""")



def inject_custom_css():
    """CupNavis samlade visuella tema: ljust, konsekvent och med hög läsbarhet."""
    st.markdown(
        """
        <style>
          :root {
            --cup-ink:#172033;
            --cup-ink-soft:#334155;
            --cup-muted:#5b6878;
            --cup-bg:#f4f7fa;
            --cup-surface:#ffffff;
            --cup-surface-soft:#eef3f7;
            --cup-border:#cfd8e3;
            --cup-border-strong:#b8c5d3;
            --cup-green:#166534;
            --cup-green-hover:#14532d;
            --cup-blue:#1e3a5f;
            --cup-focus:#2563eb;
            --cup-danger:#991b1b;
            --cup-warning:#92400e;
          }

          /* ---------- Grundyta och typografi ---------- */
          html, body, .stApp {
            background:var(--cup-bg) !important;
            color:var(--cup-ink) !important;
          }
          .stApp { min-height:100vh; }
          [data-testid="stHeader"] { background:rgba(244,247,250,.96) !important; }
          [data-testid="stToolbar"] { color:var(--cup-ink) !important; }
          .block-container {
            padding-top:1.35rem;
            padding-bottom:3rem;
            max-width:1480px;
          }
          .stApp h1,.stApp h2,.stApp h3,.stApp h4,.stApp h5,.stApp h6 {
            color:var(--cup-ink) !important;
            letter-spacing:-.015em;
            line-height:1.2;
          }
          .stApp h1 { font-weight:800; }
          .stApp h2,.stApp h3 { font-weight:750; }
          .stApp p,.stApp li,.stApp label,.stApp small,
          .stApp [data-testid="stMarkdownContainer"],
          .stApp [data-testid="stCaptionContainer"],
          .stApp [data-testid="stWidgetLabel"],
          .stApp [data-testid="stMetricLabel"] {
            color:var(--cup-ink-soft) !important;
          }
          .stApp [data-testid="stCaptionContainer"],
          .stApp [data-testid="stCaptionContainer"] p {
            color:var(--cup-muted) !important;
          }
          .stApp a { color:#1d4ed8 !important; text-decoration-color:#93c5fd; }
          .stApp hr { border-color:var(--cup-border) !important; }

          /* ---------- ÅTERÖPPNA DOLD SIDOMENY v70 ---------- */
          [data-testid="collapsedControl"],
          [data-testid="stSidebarCollapsedControl"] {
            display:flex !important;
            visibility:visible !important;
            opacity:1 !important;
            position:fixed !important;
            top:10px !important;
            left:10px !important;
            z-index:1000000 !important;
            width:auto !important;
            height:auto !important;
            pointer-events:auto !important;
          }

          [data-testid="collapsedControl"] button,
          [data-testid="stSidebarCollapsedControl"] button {
            display:flex !important;
            visibility:visible !important;
            opacity:1 !important;
            align-items:center !important;
            justify-content:center !important;
            width:42px !important;
            min-width:42px !important;
            height:42px !important;
            min-height:42px !important;
            padding:0 !important;
            border:1px solid #94a3b8 !important;
            border-radius:11px !important;
            background:#ffffff !important;
            color:#172033 !important;
            box-shadow:0 4px 14px rgba(15,23,42,.18) !important;
            cursor:pointer !important;
            pointer-events:auto !important;
          }

          [data-testid="collapsedControl"] button svg,
          [data-testid="stSidebarCollapsedControl"] button svg {
            color:#172033 !important;
            fill:#172033 !important;
            stroke:#172033 !important;
            width:22px !important;
            height:22px !important;
          }

          [data-testid="collapsedControl"] button:hover,
          [data-testid="stSidebarCollapsedControl"] button:hover {
            background:#f1f5f9 !important;
            border-color:#64748b !important;
          }

          @media (max-width:768px) {
            [data-testid="collapsedControl"],
            [data-testid="stSidebarCollapsedControl"] {
              top:8px !important;
              left:8px !important;
            }

            [data-testid="collapsedControl"] button,
            [data-testid="stSidebarCollapsedControl"] button {
              width:46px !important;
              min-width:46px !important;
              height:46px !important;
              min-height:46px !important;
            }
          }

          /* ---------- Sidomeny: alltid ljus ---------- */
          [data-testid="stSidebar"] {
            background:#eaf0f5 !important;
            border-right:1px solid var(--cup-border) !important;
          }
          [data-testid="stSidebar"] > div { background:#eaf0f5 !important; }
          [data-testid="stSidebar"] h1,
          [data-testid="stSidebar"] h2,
          [data-testid="stSidebar"] h3,
          [data-testid="stSidebar"] p,
          [data-testid="stSidebar"] label,
          [data-testid="stSidebar"] span,
          [data-testid="stSidebar"] small,
          [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {
            color:var(--cup-ink) !important;
          }

          /* ---------- Formulär, containers och expanders ---------- */
          [data-testid="stForm"],
          [data-testid="stVerticalBlockBorderWrapper"] {
            background:var(--cup-surface) !important;
            border-color:var(--cup-border) !important;
            border-radius:14px !important;
          }
          details[data-testid="stExpander"] {
            background:var(--cup-surface) !important;
            border:1px solid var(--cup-border) !important;
            border-radius:12px !important;
            overflow:hidden;
          }
          details[data-testid="stExpander"] summary {
            background:#f7f9fb !important;
            color:var(--cup-ink) !important;
          }
          details[data-testid="stExpander"] summary * { color:var(--cup-ink) !important; }

          /* ---------- Inmatningsfält ---------- */
          [data-baseweb="input"],
          [data-baseweb="textarea"],
          [data-baseweb="select"] > div,
          [data-testid="stNumberInput"] [data-baseweb="input"],
          [data-testid="stDateInput"] [data-baseweb="input"],
          [data-testid="stTimeInput"] [data-baseweb="input"] {
            background:var(--cup-surface) !important;
            color:var(--cup-ink) !important;
            border-color:var(--cup-border-strong) !important;
          }
          .stApp input,
          .stApp textarea,
          .stApp [data-baseweb="select"] input,
          .stApp [data-baseweb="select"] span,
          .stApp [data-baseweb="select"] div {
            color:var(--cup-ink) !important;
          }
          .stApp input,
          .stApp textarea {
            background:var(--cup-surface) !important;
            caret-color:var(--cup-ink) !important;
          }
          .stApp input::placeholder,.stApp textarea::placeholder {
            color:#718096 !important;
            opacity:1 !important;
          }
          [data-baseweb="input"]:focus-within,
          [data-baseweb="textarea"]:focus-within,
          [data-baseweb="select"] > div:focus-within {
            border-color:var(--cup-focus) !important;
            box-shadow:0 0 0 1px var(--cup-focus) !important;
          }

          /* Dropdown-menyer renderas ibland utanför .stApp. */
          [role="listbox"], [data-baseweb="popover"] {
            background:var(--cup-surface) !important;
            color:var(--cup-ink) !important;
          }
          [role="option"], [role="option"] * {
            color:var(--cup-ink) !important;
          }
          [role="option"]:hover { background:#eef4f8 !important; }
          [aria-selected="true"][role="option"] { background:#e2edf5 !important; }


          /* ---------- Kalender / datumväljare ---------- */
          [data-baseweb="calendar"],
          [data-baseweb="calendar"] > div,
          [data-baseweb="calendar"] table,
          [data-baseweb="calendar"] tbody,
          [data-baseweb="calendar"] thead {
            background:#ffffff !important;
            color:#172033 !important;
          }
          [data-baseweb="calendar"] *,
          [data-baseweb="calendar"] button,
          [data-baseweb="calendar"] th,
          [data-baseweb="calendar"] td,
          [data-baseweb="calendar"] div,
          [data-baseweb="calendar"] span {
            color:#172033 !important;
          }
          [data-baseweb="calendar"] button {
            background:#ffffff !important;
            border-color:transparent !important;
          }
          [data-baseweb="calendar"] button:hover {
            background:#eaf2f7 !important;
          }
          [data-baseweb="calendar"] [aria-selected="true"],
          [data-baseweb="calendar"] [aria-selected="true"] *,
          [data-baseweb="calendar"] button[aria-selected="true"],
          [data-baseweb="calendar"] button[aria-selected="true"] * {
            background:#166534 !important;
            color:#ffffff !important;
            border-radius:8px !important;
          }
          [data-baseweb="calendar"] [aria-disabled="true"],
          [data-baseweb="calendar"] [aria-disabled="true"] * {
            color:#8a98a8 !important;
          }
          [data-baseweb="calendar"] [aria-current="date"] {
            outline:2px solid #2563eb !important;
            outline-offset:-2px !important;
          }

          /* ---------- Checkbox, radio och toggles ---------- */
          [data-testid="stCheckbox"] label,
          [data-testid="stRadio"] label,
          [data-testid="stToggle"] label,
          [data-testid="stCheckbox"] span,
          [data-testid="stRadio"] span,
          [data-testid="stToggle"] span {
            color:var(--cup-ink) !important;
          }

          /* ---------- Segmenterade knappar ----------
             Streamlit kan annars ärva mörka theme-färger här.
             Håll alla segmenterade kontroller ljusa och CupNavi-enhetliga. */
          [data-testid="stSegmentedControl"] button,
          [data-testid="stButtonGroup"] button,
          [data-testid="stSegmentedControl"] [role="button"],
          [data-testid="stButtonGroup"] [role="button"] {
            background:#F8FAFC !important;
            color:#172033 !important;
            border-color:#CBD5E1 !important;
            opacity:1 !important;
            box-shadow:none !important;
          }
          [data-testid="stSegmentedControl"] button *,
          [data-testid="stButtonGroup"] button *,
          [data-testid="stSegmentedControl"] [role="button"] *,
          [data-testid="stButtonGroup"] [role="button"] * {
            color:#172033 !important;
            opacity:1 !important;
          }
          [data-testid="stSegmentedControl"] button:hover,
          [data-testid="stButtonGroup"] button:hover,
          [data-testid="stSegmentedControl"] [role="button"]:hover,
          [data-testid="stButtonGroup"] [role="button"]:hover {
            background:#EEF6F0 !important;
            border-color:#86A995 !important;
          }
          [data-testid="stSegmentedControl"] button[aria-pressed="true"],
          [data-testid="stButtonGroup"] button[aria-pressed="true"],
          [data-testid="stSegmentedControl"] [role="button"][aria-pressed="true"],
          [data-testid="stButtonGroup"] [role="button"][aria-pressed="true"],
          [data-testid="stSegmentedControl"] button[aria-checked="true"],
          [data-testid="stButtonGroup"] button[aria-checked="true"],
          [data-testid="stSegmentedControl"] [data-selected="true"],
          [data-testid="stButtonGroup"] [data-selected="true"] {
            background:#DCFCE7 !important;
            color:#14532D !important;
            border-color:#86A995 !important;
            font-weight:800 !important;
          }
          [data-testid="stSegmentedControl"] button[aria-pressed="true"] *,
          [data-testid="stButtonGroup"] button[aria-pressed="true"] *,
          [data-testid="stSegmentedControl"] [role="button"][aria-pressed="true"] *,
          [data-testid="stButtonGroup"] [role="button"][aria-pressed="true"] *,
          [data-testid="stSegmentedControl"] button[aria-checked="true"] *,
          [data-testid="stButtonGroup"] button[aria-checked="true"] *,
          [data-testid="stSegmentedControl"] [data-selected="true"] *,
          [data-testid="stButtonGroup"] [data-selected="true"] * {
            color:#14532D !important;
            opacity:1 !important;
          }

          /* ---------- Knappar ---------- */
          .stButton > button,
          .stFormSubmitButton > button,
          .stDownloadButton > button {
            background:var(--cup-surface) !important;
            color:var(--cup-ink) !important;
            border:1px solid var(--cup-border-strong) !important;
            border-radius:10px !important;
            font-weight:700 !important;
            min-height:2.55rem;
            box-shadow:0 1px 2px rgba(15,23,42,.04);
            transition:background .12s ease,border-color .12s ease,box-shadow .12s ease;
          }
          .stButton > button p,.stButton > button span,
          .stFormSubmitButton > button p,.stFormSubmitButton > button span,
          .stDownloadButton > button p,.stDownloadButton > button span {
            color:var(--cup-ink) !important;
          }
          .stButton > button:hover,
          .stFormSubmitButton > button:hover,
          .stDownloadButton > button:hover {
            background:#f2f6f9 !important;
            border-color:#98a9bb !important;
            box-shadow:0 3px 9px rgba(15,23,42,.08);
          }
          button[kind="primary"],
          .stButton > button[kind="primary"],
          .stFormSubmitButton > button[kind="primary"] {
            background:var(--cup-green) !important;
            border-color:var(--cup-green) !important;
            color:#ffffff !important;
          }
          button[kind="primary"] p,button[kind="primary"] span,
          .stButton > button[kind="primary"] p,.stButton > button[kind="primary"] span,
          .stFormSubmitButton > button[kind="primary"] p,.stFormSubmitButton > button[kind="primary"] span {
            color:#ffffff !important;
          }
          button[kind="primary"]:hover { background:var(--cup-green-hover) !important; }
          button:disabled,button:disabled * {
            color:#7b8794 !important;
            opacity:1 !important;
          }
          button:disabled { background:#edf1f4 !important; border-color:#d7dee6 !important; }

          /* ---------- Metrics ---------- */
          div[data-testid="stMetric"] {
            background:var(--cup-surface) !important;
            border:1px solid var(--cup-border) !important;
            border-radius:12px !important;
            padding:13px 15px !important;
            box-shadow:none !important;
          }
          div[data-testid="stMetricLabel"],div[data-testid="stMetricLabel"] * {
            color:var(--cup-muted) !important;
          }
          div[data-testid="stMetricValue"],div[data-testid="stMetricValue"] * {
            color:var(--cup-ink) !important;
            font-weight:800 !important;
          }

          /* ---------- Informations-, varnings- och felrutor ---------- */
          [data-testid="stAlert"] {
            border-radius:10px !important;
            border:1px solid var(--cup-border) !important;
          }
          [data-testid="stAlert"] p,[data-testid="stAlert"] div,[data-testid="stAlert"] span {
            color:var(--cup-ink) !important;
          }
          [data-testid="stNotification"] * { color:var(--cup-ink) !important; }

          /* ---------- Tabeller och data ---------- */
          .stApp table {
            background:var(--cup-surface) !important;
            color:var(--cup-ink) !important;
            border-color:var(--cup-border) !important;
          }
          .stApp table th {
            background:#e9eff4 !important;
            color:var(--cup-ink) !important;
            font-weight:750 !important;
          }
          .stApp table td { color:var(--cup-ink) !important; }
          [data-testid="stDataFrame"] {
            background:var(--cup-surface) !important;
            border:1px solid var(--cup-border) !important;
            border-radius:10px !important;
            overflow:hidden;
          }

          /* ---------- Publik hero och matchkort ---------- */
          /* v91 public navigation + info */
          .cn-rules-grid {
            display:grid;
            grid-template-columns:repeat(2,minmax(0,1fr));
            gap:12px;
            margin:10px 0 20px;
          }
          .cn-rule-card {
            display:flex;
            gap:12px;
            align-items:flex-start;
            padding:16px;
            border:1px solid #dbe3ea;
            border-radius:16px;
            background:linear-gradient(145deg,#ffffff,#f7f9fc);
            box-shadow:0 5px 16px rgba(15,23,42,.06);
          }
          .cn-rule-icon {
            width:38px;height:38px;border-radius:12px;
            display:flex;align-items:center;justify-content:center;
            background:#eef4ff;font-size:20px;flex:0 0 38px;
          }
          .cn-rule-card strong {display:block;color:#172033;font-size:15px;margin-bottom:4px}
          .cn-rule-card span {display:block;color:#334155;line-height:1.45;font-size:14px}
          .cn-rule-card small {display:block;color:#64748b;margin-top:4px}
          .cn-custom-info-card,.cn-practical-info-card {
            border:1px solid #dbe3ea;border-radius:16px;padding:17px 18px;
            background:#fff;box-shadow:0 4px 14px rgba(15,23,42,.05);
            line-height:1.6;color:#172033;margin:8px 0 18px;
          }
          .cn-practical-info-card {display:grid;gap:10px}
          @media (max-width:680px) {
            .cn-rules-grid {grid-template-columns:1fr}
            div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] button {
              min-height:64px;
              border-radius:15px;
              font-weight:850;
              font-size:14px;
              box-shadow:0 4px 12px rgba(15,23,42,.08);
            }
          }

          .cup-hero {
            background:linear-gradient(135deg,#172033 0%,#1e3a5f 58%,#166534 120%);
            color:#ffffff !important;
            border-radius:16px;
            padding:22px 24px;
            margin:4px 0 18px;
            box-shadow:0 8px 20px rgba(15,23,42,.14);
          }
          .cup-hero,.cup-hero h1,.cup-hero h2,.cup-hero h3,.cup-hero h4,
          .cup-hero p,.cup-hero div,.cup-hero span,.cup-hero b,.cup-hero small {
            color:#ffffff !important;
          }
          .cup-hero .eyebrow { font-size:12px; text-transform:uppercase; letter-spacing:.11em; opacity:.82; font-weight:800; }
          .cup-hero .title { font-size:clamp(26px,4vw,40px); font-weight:850; line-height:1.08; margin:5px 0 8px; }
          .cup-hero .meta { font-size:14px; opacity:.94; }

          .status-pill { display:inline-block; padding:4px 9px; border-radius:999px; font-size:11px; font-weight:800; letter-spacing:.03em; }
          .status-live { background:#dcfce7 !important; color:#14532d !important; }
          .status-upcoming { background:#dbeafe !important; color:#1e40af !important; }
          .status-finished { background:#e2e8f0 !important; color:#334155 !important; }
          .public-match-card {
            background:var(--cup-surface) !important;
            color:var(--cup-ink) !important;
            border-color:var(--cup-border) !important;
            box-shadow:0 2px 8px rgba(15,23,42,.06) !important;
            transition:border-color .15s ease,box-shadow .15s ease;
          }
          .public-match-card,.public-match-card div,.public-match-card p,
          .public-match-card b,.public-match-card small {
            color:var(--cup-ink) !important;
          }
          .public-match-card .match-stage { color:#ffffff !important; }
          .public-match-card .match-meta { color:var(--cup-ink-soft) !important; }
          .public-match-card .match-weather,.public-match-card .match-referee,
          .public-match-card .kit-label { color:var(--cup-muted) !important; }
          .public-match-card:hover {
            box-shadow:0 5px 14px rgba(15,23,42,.10) !important;
            border-color:#aebdca !important;
          }

          /* ---------- Versionsmärke ---------- */
          .cup-version-badge {
            display:inline-block;
            margin:2px 0 12px;
            padding:6px 10px;
            border-radius:7px;
            background:#e4efe8;
            border:1px solid #b9d2c1;
            color:#14532d !important;
            font-size:12px;
            font-weight:800;
            letter-spacing:.02em;
          }

          /* ---------- Publik statistik ---------- */
          .public-metric-grid {
            display:grid;
            grid-template-columns:repeat(4,minmax(0,1fr));
            gap:12px;
            margin:0 0 16px;
          }
          .public-metric {
            background:#ffffff;
            border:1px solid var(--cup-border);
            border-radius:12px;
            padding:13px 15px;
            min-height:82px;
          }
          .public-metric .label { color:var(--cup-muted) !important; font-size:13px; margin-bottom:6px; }
          .public-metric .value { color:var(--cup-ink) !important; font-size:30px; line-height:1; font-weight:850; }


          /* ---------- Mobilkompatibilitet: iOS + Android ---------- */
          html, body {
            -webkit-text-size-adjust:100% !important;
            text-size-adjust:100% !important;
          }

          /* Undvik iOS auto-zoom när användaren trycker i formulärfält. */
          input, textarea, select,
          [data-baseweb="input"] input,
          [data-baseweb="textarea"] textarea,
          [data-baseweb="select"] input {
            font-size:16px !important;
          }


          /* Datumfält: tydlig kontrast även när Safari använder native-kontroll. */
          input[type="date"],
          input[type="time"] {
            background:#ffffff !important;
            color:#172033 !important;
            color-scheme:light !important;
            min-height:44px !important;
          }
          input[type="date"]::-webkit-date-and-time-value,
          input[type="time"]::-webkit-date-and-time-value {
            color:#172033 !important;
            text-align:left;
          }
          input[type="date"]::-webkit-calendar-picker-indicator,
          input[type="time"]::-webkit-calendar-picker-indicator {
            opacity:.85;
          }


          /* Dataframes får inte pressa hela sidan bredare än mobilen. */
          [data-testid="stDataFrame"],
          [data-testid="stDataEditor"] {
            max-width:100% !important;
            overflow-x:auto !important;
            -webkit-overflow-scrolling:touch !important;
          }

          @supports (padding: max(0px)) {
            .stApp .block-container {
              padding-left:max(.65rem, env(safe-area-inset-left)) !important;
              padding-right:max(.65rem, env(safe-area-inset-right)) !important;
              padding-bottom:max(1rem, env(safe-area-inset-bottom)) !important;
            }
          }

          @media (max-width:760px) {
            /* Rubriker får brytas utan att skapa horisontell scroll. */
            h1, h2, h3, h4, .cup-hero .title {
              overflow-wrap:anywhere;
              word-break:normal;
            }


            /* Matchkort ska hålla sig inom viewport. */
            .public-match-card {
              max-width:100% !important;
              overflow:hidden !important;
            }

            /* Formulär i flera kolumner får bli en kolumn på mycket smala telefoner. */
            div[data-testid="stHorizontalBlock"] {
              gap:.55rem !important;
            }
          }

          @media (max-width:430px) {
            .block-container {
              padding-top:.35rem !important;
            }
            .cup-version-badge {
              font-size:11px !important;
              padding:5px 8px !important;
            }
            .cup-hero .title {
              font-size:24px !important;
            }
            .public-metric .value {
              font-size:23px !important;
            }
          }

          /* iOS/Safari-specifikt – påverkar inte Android. */
          @supports (-webkit-touch-callout:none) {
            body {
              -webkit-font-smoothing:antialiased;
            }
            input, textarea, select, button {
              -webkit-appearance:none;
            }
            input[type="checkbox"],
            input[type="radio"] {
              -webkit-appearance:auto;
            }
          }

          /* ---------- Mobil ---------- */
          @media (max-width:760px) {
            .block-container { padding-left:.65rem; padding-right:.65rem; padding-top:.55rem; }
            .cup-hero { padding:15px 14px; border-radius:13px; margin-top:8px; margin-bottom:12px; }
            .cup-hero .title { font-size:27px; }
            .public-metric-grid { grid-template-columns:repeat(2,minmax(0,1fr)); gap:9px; margin-bottom:12px; }
            .public-metric { min-height:70px; padding:11px 12px; }
            .public-metric .value { font-size:25px; }
            .public-match-card { padding:11px !important; }
            .public-match-card .public-team-name { font-size:15px !important; }
            .public-match-card .kit-label { display:none !important; }
            .public-match-card .match-meta { font-size:12px !important; line-height:1.35 !important; }
            div[data-baseweb="tab-list"] {
              border-radius:9px !important;
              overflow-x:auto !important;
              flex-wrap:nowrap !important;
              scrollbar-width:none;
            }
            div[data-baseweb="tab-list"]::-webkit-scrollbar { display:none; }
            button[data-baseweb="tab"] { min-height:40px; white-space:nowrap !important; padding-left:10px !important; padding-right:10px !important; }
            div[role="radiogroup"] { gap:.25rem !important; }
          }



          /* ===== CENTRAL NAVIGATION v29 =====
             Alla navigationsval använder vanliga Streamlit-knappar.
             Inaktiv = ljus yta + mörk text.
             Aktiv = grön yta + vit text.
          */
          .stButton > button,
          .stFormSubmitButton > button,
          .stDownloadButton > button {
            background:#FFFFFF !important;
            border:1px solid #B8C5D1 !important;
            color:#0F172A !important;
            opacity:1 !important;
          }
          .stButton > button *,
          .stFormSubmitButton > button *,
          .stDownloadButton > button * {
            color:#0F172A !important;
            opacity:1 !important;
          }
          .stButton > button:hover,
          .stFormSubmitButton > button:hover,
          .stDownloadButton > button:hover {
            background:#F1F5F9 !important;
            border-color:#94A3B8 !important;
          }

          .stButton > button[kind="primary"],
          .stFormSubmitButton > button[kind="primary"] {
            background:#166534 !important;
            border-color:#166534 !important;
            color:#FFFFFF !important;
            opacity:1 !important;
          }
          .stButton > button[kind="primary"] *,
          .stFormSubmitButton > button[kind="primary"] * {
            color:#FFFFFF !important;
            opacity:1 !important;
          }
          .stButton > button[kind="primary"]:hover,
          .stFormSubmitButton > button[kind="primary"]:hover {
            background:#14532D !important;
            border-color:#14532D !important;
          }

          /* Publika flikar ligger kvar överst när användaren scrollar. */
          div[data-baseweb="tab-list"] {
            position:sticky !important;
            top:0 !important;
            z-index:999 !important;
            box-shadow:0 4px 10px rgba(15,23,42,.10) !important;
          }

          /* Publika st.tabs finns kvar men får ett enda tydligt färgsystem. */
          div[data-baseweb="tab-list"] {
            background:#F1F5F9 !important;
            border:1px solid #CBD5E1 !important;
            isolation:isolate !important;
            border-radius:10px !important;
            padding:4px !important;
            gap:3px !important;
            overflow-x:auto !important;
          }
          button[data-baseweb="tab"],
          button[data-baseweb="tab"] > div {
            background:#FFFFFF !important;
            color:#0F172A !important;
            opacity:1 !important;
          }
          button[data-baseweb="tab"] *,
          button[data-baseweb="tab"] p,
          button[data-baseweb="tab"] span {
            color:#0F172A !important;
            opacity:1 !important;
          }
          button[data-baseweb="tab"][aria-selected="true"],
          button[data-baseweb="tab"][aria-selected="true"] > div {
            background:#DCFCE7 !important;
            color:#14532D !important;
            font-weight:800 !important;
          }
          button[data-baseweb="tab"][aria-selected="true"] * {
            color:#14532D !important;
          }

          @media (max-width:760px) {
            .stButton > button {
              min-height:44px !important;
              font-size:14px !important;
            }
            div[data-baseweb="tab-list"] {
              flex-wrap:nowrap !important;
              overflow-x:auto !important;
              -webkit-overflow-scrolling:touch !important;
              scrollbar-width:none;
            }
            div[data-baseweb="tab-list"]::-webkit-scrollbar { display:none; }
            button[data-baseweb="tab"] {
              flex:0 0 auto !important;
              min-height:44px !important;
              white-space:nowrap !important;
              padding-left:12px !important;
              padding-right:12px !important;
            }
          }


          /* ===== TABELLER v31: centrera rubriker och innehåll ===== */
          table th,
          table td {
            text-align:center !important;
            vertical-align:middle !important;
          }

          /* Streamlit dataframe/data_editor (Glide Data Grid) */
          [data-testid="stDataFrame"] [role="columnheader"],
          [data-testid="stDataFrame"] [role="gridcell"],
          [data-testid="stDataEditor"] [role="columnheader"],
          [data-testid="stDataEditor"] [role="gridcell"] {
            text-align:center !important;
            justify-content:center !important;
            align-items:center !important;
          }

          [data-testid="stDataFrame"] [role="columnheader"] *,
          [data-testid="stDataFrame"] [role="gridcell"] *,
          [data-testid="stDataEditor"] [role="columnheader"] *,
          [data-testid="stDataEditor"] [role="gridcell"] * {
            text-align:center !important;
            justify-content:center !important;
            margin-left:auto !important;
            margin-right:auto !important;
          }

</style>
        """,
        unsafe_allow_html=True,
    )


inject_custom_css()

# Global CupNavi-identitet. Logotypen ligger lokalt i releasen så den inte kräver
# nätverksanrop. Den renderas som en liten integrerad brand-rad i appskalet och
# ligger kvar i alla vyer under scrollning.
CUPNAVI_LOGO_FILE = Path(__file__).with_name("assets") / "cupnavi_logo.png"


def render_persistent_brand():
    try:
        logo_b64 = base64.b64encode(CUPNAVI_LOGO_FILE.read_bytes()).decode("ascii")
    except OSError:
        return
    st.markdown(
        f"""
        <style>
          .cn-persistent-brand {{
            position:fixed;
            top:10px;
            left:50%;
            transform:translateX(-50%);
            z-index:999997;
            display:flex;
            align-items:center;
            justify-content:center;
            min-width:210px;
            max-width:min(360px, calc(100vw - 28px));
            padding:8px 14px;
            border:1px solid rgba(203, 213, 225, 0.88);
            border-radius:999px;
            background:linear-gradient(180deg, rgba(255,255,255,.98), rgba(248,250,252,.95));
            box-shadow:0 10px 26px rgba(15,23,42,.10);
            backdrop-filter:blur(10px);
            -webkit-backdrop-filter:blur(10px);
            pointer-events:none;
          }}
          .cn-persistent-brand img {{
            display:block;
            width:min(100%, 270px);
            height:auto;
          }}
          .stApp .block-container {{
            padding-top:4.85rem !important;
          }}
          @media (max-width:760px) {{
            .cn-persistent-brand {{
              top:8px;
              min-width:auto;
              width:calc(100vw - 18px);
              max-width:280px;
              padding:6px 10px;
              border-radius:18px;
              box-shadow:0 8px 20px rgba(15,23,42,.11);
            }}
            .cn-persistent-brand img {{
              width:min(100%, 215px);
            }}
            .stApp .block-container {{
              padding-top:4.45rem !important;
            }}
          }}
        </style>
        <div class="cn-persistent-brand" aria-label="CupNavi">
          <img src="data:image/png;base64,{logo_b64}" alt="CupNavi logotyp">
        </div>
        """,
        unsafe_allow_html=True,
    )


render_persistent_brand()
# APP_VERSION centraliseras i cupnavi_core/version.py
DB_FILE = Path(__file__).with_name("turnering.db")


def setting(name):
    """Hämta en hemlighet från Streamlit Secrets eller en miljövariabel."""
    try:
        value = st.secrets.get(name)
    except (FileNotFoundError, KeyError):
        value = None
    return str(value).strip() if value else os.getenv(name, "").strip()


TURSO_DATABASE_URL = setting("TURSO_DATABASE_URL")
TURSO_AUTH_TOKEN = setting("TURSO_AUTH_TOKEN")
CLOUD_DATABASE_ENABLED = bool(TURSO_DATABASE_URL and TURSO_AUTH_TOKEN)


def require_admin_access():
    """Kräv adminlösenord i webbdrift. Lokalt läge får köras utan lösenord."""
    admin_password = setting("ADMIN_PASSWORD")
    if not admin_password:
        if CLOUD_DATABASE_ENABLED:
            st.sidebar.error("Adminlösenord saknas i Streamlit Secrets.")
            st.error("Administration är låst tills ADMIN_PASSWORD har lagts till i Streamlit Secrets.")
            st.stop()
        st.sidebar.warning("Lokalt läge utan adminlösenord")
        return

    if st.session_state.get("admin_authenticated"):
        st.sidebar.success("Inloggad som administratör")
        if st.sidebar.button("Logga ut", use_container_width=True):
            st.session_state["admin_authenticated"] = False
            st.rerun()
        return

    st.title("Administratörsinloggning")
    st.caption("Turneringsvyn är offentlig. Administrationen kräver lösenord.")
    with st.form("admin_login"):
        entered_password = st.text_input("Adminlösenord", type="password")
        submitted = st.form_submit_button(tr("Logga in"), type="primary", use_container_width=True)
    if submitted:
        if hmac.compare_digest(entered_password, admin_password):
            # Form-submitten har redan startat den aktuella renderingen.
            # Fortsätt direkt till administrationen i samma körning i stället
            # för att tvinga fram ännu en full omladdning mot Turso.
            st.session_state["admin_authenticated"] = True
            st.rerun()
        st.error(tr("Fel lösenord."))
    st.stop()


def require_match_reporter_access():
    """Separat, begränsad inloggning för resultat och matchhändelser."""
    reporter_password = setting("MATCH_REPORTER_PASSWORD") or "123"

    if st.session_state.get("reporter_authenticated"):
        st.sidebar.success("Inloggad som matchrapportör")
        if st.sidebar.button("Logga ut", key="reporter_logout", use_container_width=True):
            st.session_state["reporter_authenticated"] = False
            st.rerun()
        return

    st.title(tr("Matchrapportör"))
    st.caption("Den här rollen kan endast rapportera matchresultat och matchhändelser.")
    with st.form("match_reporter_login"):
        entered_password = st.text_input(tr("Lösenord"), type="password")
        submitted = st.form_submit_button("Logga in", type="primary", use_container_width=True)
    if submitted:
        if hmac.compare_digest(entered_password, reporter_password):
            st.session_state["reporter_authenticated"] = True
            st.rerun()
        st.error("Fel lösenord.")
    st.stop()


class CloudConnection:
    """DB-API-adapter som återanvänder Turso-anslutningen under Streamlit-sessionen."""
    def __init__(self, raw):
        self.raw = raw
        self._dirty = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        # Turso-anslutningen hålls öppen mellan appens reruns. Att öppna/stänga en
        # nätverksanslutning för varje SELECT var den största prestandaflaskhalsen.
        if exc_type is None:
            if self._dirty:
                self.commit()
        else:
            self.rollback()
        return False

    @staticmethod
    def _is_write(sql):
        first = sql.lstrip().split(None, 1)[0].upper() if sql and sql.strip() else ""
        return first not in {"SELECT", "PRAGMA", "EXPLAIN"}

    def execute(self, sql, params=()):
        is_write = self._is_write(sql)
        if is_write:
            self._dirty = True
        try:
            return self.raw.execute(sql, params)
        except Exception:
            # En tappad/stängd Turso-anslutning ska inte kräva en separat
            # SELECT 1 före varje normal fråga. Läsfrågor får i stället
            # en enda säker återanslutning först när ett verkligt fel uppstår.
            if is_write:
                raise
            fresh = _new_cloud_raw_connection()
            st.session_state["_cupnavi_turso_connection"] = fresh
            self.raw = fresh
            return self.raw.execute(sql, params)

    def executemany(self, sql, params):
        if self._is_write(sql):
            self._dirty = True
        return self.raw.executemany(sql, params)

    def commit(self):
        result = self.raw.commit()
        self._dirty = False
        return result

    def rollback(self):
        rollback = getattr(self.raw, "rollback", None)
        self._dirty = False
        return rollback() if rollback else None

    def close(self):
        # Medvetet no-op i webbdrift. Sessionens anslutning återanvänds för att
        # slippa nätverks-handshake vid varje liten databasfråga.
        return None


def _new_cloud_raw_connection():
    try:
        import libsql
    except ImportError as exc:
        raise RuntimeError(
            "Turso är konfigurerat men Python-paketet libsql saknas. "
            "Installera requirements.txt."
        ) from exc
    return libsql.connect(database=TURSO_DATABASE_URL, auth_token=TURSO_AUTH_TOKEN)


def _cloud_raw_connection():
    """Återanvänd Turso-anslutningen utan ett extra nätverksanrop före varje fråga."""
    raw = st.session_state.get("_cupnavi_turso_connection")
    if raw is None:
        raw = _new_cloud_raw_connection()
        st.session_state["_cupnavi_turso_connection"] = raw
    return raw


def db():
    """Använd Turso i molnet och lokal SQLite på utvecklingsdatorn."""
    if CLOUD_DATABASE_ENABLED:
        return CloudConnection(_cloud_raw_connection())

    con = sqlite3.connect(DB_FILE)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def _rows_from_cursor(cursor):
    """Normalisera både sqlite3.Row och libsql-tupler till dictionary-liknande rader."""
    rows = cursor.fetchall()
    if not rows:
        return []
    if isinstance(rows[0], sqlite3.Row):
        return rows
    description = getattr(cursor, "description", None) or []
    names = [column[0] for column in description]
    if names:
        return [dict(zip(names, row)) for row in rows]
    return rows


def _one_from_cursor(cursor):
    row = cursor.fetchone()
    if row is None or isinstance(row, sqlite3.Row):
        return row
    description = getattr(cursor, "description", None) or []
    names = [column[0] for column in description]
    return dict(zip(names, row)) if names else row


def execute_script(con, script):
    """Kör ett SQL-script även när anslutningen saknar sqlite3.executescript."""
    if not CLOUD_DATABASE_ENABLED and hasattr(con, "executescript"):
        return con.executescript(script)
    buffer = ""
    for line in script.splitlines(True):
        buffer += line
        if sqlite3.complete_statement(buffer):
            statement = buffer.strip()
            if statement:
                con.execute(statement)
            buffer = ""
    if buffer.strip():
        con.execute(buffer)


def columns(table):
    with db() as con:
        cursor = con.execute(f"PRAGMA table_info({table})")
        return {row["name"] for row in _rows_from_cursor(cursor)}


def _connection_columns(con, table):
    cursor = con.execute(f"PRAGMA table_info({table})")
    return {row["name"] for row in _rows_from_cursor(cursor)}


def ensure_v96_experience_schema_compat(con):
    """
    Självläkande kompatibilitetslager för v96+-data.

    Det här skyddar särskilt mot en ofullständig GitHub-upload där ny app.py
    har publicerats tillsammans med en äldre migrationsmodul. Alla operationer
    är idempotenta och migration 5 markeras först efter att hela minimischemat
    finns på plats.
    """
    con.execute(
        """CREATE TABLE IF NOT EXISTS cupnavi_schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TEXT NOT NULL
        )"""
    )

    tournament_cols = _connection_columns(con, "tournaments")
    team_cols = _connection_columns(con, "teams")
    match_cols = _connection_columns(con, "matches")

    if "sport" not in tournament_cols:
        con.execute("ALTER TABLE tournaments ADD COLUMN sport TEXT NOT NULL DEFAULT 'Fotboll'")
    if "checked_in" not in team_cols:
        con.execute("ALTER TABLE teams ADD COLUMN checked_in INTEGER NOT NULL DEFAULT 0")
    if "checked_in_at" not in team_cols:
        con.execute("ALTER TABLE teams ADD COLUMN checked_in_at TEXT")
    if "original_scheduled_start" not in match_cols:
        con.execute("ALTER TABLE matches ADD COLUMN original_scheduled_start TEXT")

    execute_script(
        con,
        """
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
            created_at TEXT NOT NULL,
            actor TEXT NOT NULL DEFAULT 'Admin',
            action_type TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id INTEGER,
            description TEXT NOT NULL,
            before_json TEXT,
            after_json TEXT,
            reversible INTEGER NOT NULL DEFAULT 0,
            undone_at TEXT
        );
        CREATE TABLE IF NOT EXISTS cup_feed (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
            created_at TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'Info',
            title TEXT NOT NULL,
            detail TEXT,
            public INTEGER NOT NULL DEFAULT 1,
            related_match_id INTEGER REFERENCES matches(id) ON DELETE SET NULL
        );
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
            team_id INTEGER REFERENCES teams(id) ON DELETE CASCADE,
            created_at TEXT NOT NULL,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            event_key TEXT,
            UNIQUE(tournament_id, team_id, event_key)
        );
        CREATE TABLE IF NOT EXISTS venue_points (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
            kind TEXT NOT NULL DEFAULT 'Övrigt',
            label TEXT NOT NULL,
            detail TEXT,
            url TEXT,
            sort_order INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS referee_acknowledgements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
            referee_id INTEGER NOT NULL REFERENCES referees(id) ON DELETE CASCADE,
            match_id INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
            acknowledged_at TEXT NOT NULL,
            UNIQUE(referee_id, match_id)
        );
        CREATE INDEX IF NOT EXISTS idx_audit_tournament_created ON audit_log(tournament_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_feed_tournament_created ON cup_feed(tournament_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_notifications_tournament_team ON notifications(tournament_id, team_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_venue_points_tournament ON venue_points(tournament_id, sort_order);
        CREATE INDEX IF NOT EXISTS idx_ref_ack_tournament_referee ON referee_acknowledgements(tournament_id, referee_id);
        """,
    )
    con.execute(
        "INSERT OR IGNORE INTO cupnavi_schema_migrations(version,name,applied_at) VALUES(5,?,?)",
        ("experience_toolkit_v96", datetime.now().isoformat(timespec="seconds")),
    )


def ensure_v99_team_portal_schema_compat(con):
    """Idempotent skydd för Lagportalens schema även vid blandade releasefiler."""
    tournament_cols = _connection_columns(con, "tournaments")
    team_cols = _connection_columns(con, "teams")
    tournament_additions = {
        "squad_deadline_minutes": "INTEGER NOT NULL DEFAULT 30",
        "max_roster_size": "INTEGER NOT NULL DEFAULT 0",
        "allow_team_public_contact": "INTEGER NOT NULL DEFAULT 0",
    }
    team_additions = {
        "checked_in_by": "TEXT",
        "kit_confirmed_at": "TEXT",
        "public_contact_name": "TEXT",
        "public_contact_phone": "TEXT",
        "public_contact_email": "TEXT",
        "public_contact_enabled": "INTEGER NOT NULL DEFAULT 0",
    }
    for name, ddl in tournament_additions.items():
        if name not in tournament_cols:
            con.execute(f"ALTER TABLE tournaments ADD COLUMN {name} {ddl}")
    for name, ddl in team_additions.items():
        if name not in team_cols:
            con.execute(f"ALTER TABLE teams ADD COLUMN {name} {ddl}")
    execute_script(
        con,
        """
        CREATE TABLE IF NOT EXISTS participant_access_credentials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
            team_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
            code_salt TEXT NOT NULL,
            code_hash TEXT NOT NULL,
            created_at TEXT NOT NULL,
            rotated_at TEXT,
            UNIQUE(tournament_id, team_id)
        );
        CREATE TABLE IF NOT EXISTS match_rosters (
            match_id INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
            team_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
            player_id INTEGER NOT NULL REFERENCES players(id) ON DELETE CASCADE,
            selected_at TEXT NOT NULL,
            selected_by TEXT NOT NULL DEFAULT 'Deltagaransvarig',
            PRIMARY KEY(match_id, team_id, player_id)
        );
        CREATE INDEX IF NOT EXISTS idx_participant_access_tournament_team ON participant_access_credentials(tournament_id, team_id);
        CREATE INDEX IF NOT EXISTS idx_match_rosters_match_team ON match_rosters(match_id, team_id);
        """,
    )
    con.execute(
        "INSERT OR IGNORE INTO cupnavi_schema_migrations(version,name,applied_at) VALUES(6,?,?)",
        ("participant_team_portal_v99", datetime.now().isoformat(timespec="seconds")),
    )


def ensure_v106_participant_privacy_schema_compat(con):
    """Idempotent kontakt-, spelarnamn-, integritets- och admin-kodfält för v106."""
    team_cols = _connection_columns(con, "teams")
    player_cols = _connection_columns(con, "players")
    credential_cols = _connection_columns(con, "participant_access_credentials")
    team_additions = {
        "responsible_name": "TEXT",
        "responsible_phone": "TEXT",
        "responsible_email": "TEXT",
        "responsible_contact_protected": "INTEGER NOT NULL DEFAULT 1",
    }
    player_additions = {
        "first_name": "TEXT",
        "last_name": "TEXT",
        "is_protected": "INTEGER NOT NULL DEFAULT 0",
    }
    for name, ddl in team_additions.items():
        if name not in team_cols:
            con.execute(f"ALTER TABLE teams ADD COLUMN {name} {ddl}")
    for name, ddl in player_additions.items():
        if name not in player_cols:
            con.execute(f"ALTER TABLE players ADD COLUMN {name} {ddl}")
    if "admin_code" not in credential_cols:
        con.execute("ALTER TABLE participant_access_credentials ADD COLUMN admin_code TEXT")
    con.execute(
        "INSERT OR IGNORE INTO cupnavi_schema_migrations(version,name,applied_at) VALUES(9,?,?)",
        ("participant_privacy_and_admin_codes_v106", datetime.now().isoformat(timespec="seconds")),
    )


def _player_display_name(player_row, public=False):
    """Gemensam namnvisning med stöd för skyddade spelare och legacy-fältet name."""
    if public and bool(_row_value(player_row, "is_protected", 0)):
        return "Skyddad spelare"
    first = str(_row_value(player_row, "first_name", "") or "").strip()
    last = str(_row_value(player_row, "last_name", "") or "").strip()
    full = " ".join(part for part in (first, last) if part).strip()
    return full or str(_row_value(player_row, "name", "") or "").strip() or "Spelare"


def ensure_v100_international_schema_compat(con):
    """Idempotent international/multisport fields for mixed or legacy deployments."""
    tournament_cols = _connection_columns(con, "tournaments")
    additions = {
        "locale": "TEXT NOT NULL DEFAULT 'sv-SE'",
        "timezone_name": "TEXT NOT NULL DEFAULT 'Europe/Stockholm'",
        "participant_type": "TEXT NOT NULL DEFAULT 'team'",
        "country_code": "TEXT",
    }
    for name, ddl in additions.items():
        if name not in tournament_cols:
            con.execute(f"ALTER TABLE tournaments ADD COLUMN {name} {ddl}")
    con.execute(
        "INSERT OR IGNORE INTO cupnavi_schema_migrations(version,name,applied_at) VALUES(7,?,?)",
        ("international_multisport_foundation_v100", datetime.now().isoformat(timespec="seconds")),
    )


def ensure_v102_lifecycle_schema_compat(con):
    """Idempotent cup lifecycle/history fields and permanent public slugs."""
    tournament_cols = _connection_columns(con, "tournaments")
    lifecycle_was_present = "lifecycle_status" in tournament_cols
    additions = {
        "lifecycle_status": "TEXT NOT NULL DEFAULT 'draft'",
        "public_slug": "TEXT",
        "completed_at": "TEXT",
        "trashed_at": "TEXT",
    }
    for name, ddl in additions.items():
        if name not in tournament_cols:
            con.execute(f"ALTER TABLE tournaments ADD COLUMN {name} {ddl}")

    # Preserve legacy publication state when introducing the lifecycle model.
    if not lifecycle_was_present:
        con.execute(
            "UPDATE tournaments SET lifecycle_status=CASE WHEN COALESCE(is_published,0)=1 THEN 'published' ELSE 'draft' END"
        )
    else:
        con.execute(
            "UPDATE tournaments SET lifecycle_status=CASE WHEN COALESCE(is_published,0)=1 THEN 'published' ELSE 'draft' END "
            "WHERE lifecycle_status IS NULL OR lifecycle_status='' OR lifecycle_status NOT IN ('draft','published','live','completed','trashed')"
        )

    rows = con.execute(
        "SELECT id,name,COALESCE(start_date,tournament_date) AS start_date,public_slug FROM tournaments ORDER BY id"
    ).fetchall()
    used = {row[3] for row in rows if row[3]}
    for row in rows:
        if row[3]:
            continue
        slug = choose_unique_slug(row[1], row[2], row[0], used)
        con.execute("UPDATE tournaments SET public_slug=? WHERE id=?", (slug, row[0]))
        used.add(slug)

    con.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_tournaments_public_slug ON tournaments(public_slug)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_tournaments_lifecycle_status ON tournaments(lifecycle_status)")
    con.execute(
        "INSERT OR IGNORE INTO cupnavi_schema_migrations(version,name,applied_at) VALUES(8,?,?)",
        ("tournament_lifecycle_history_v102", datetime.now().isoformat(timespec="seconds")),
    )


@st.cache_resource(show_spinner=False)
def init_db():
    """Initiera schema/migreringar en gång per app-process, inte en gång per besökare."""
    schema_key = f"{APP_VERSION}:{'cloud' if CLOUD_DATABASE_ENABLED else 'local'}"
    with db() as con:
        execute_script(
            con,
            """
            CREATE TABLE IF NOT EXISTS tournaments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                location TEXT,
                tournament_date TEXT,
                start_date TEXT,
                end_date TEXT,
                expected_team_count INTEGER NOT NULL DEFAULT 0,
                is_published INTEGER NOT NULL DEFAULT 0,
                points_win INTEGER NOT NULL DEFAULT 3,
                points_draw INTEGER NOT NULL DEFAULT 1,
                points_loss INTEGER NOT NULL DEFAULT 0,
                playoff_format TEXT NOT NULL DEFAULT 'Inget slutspel',
                bronze_match INTEGER NOT NULL DEFAULT 0,
                arena_address TEXT,
                kiosk_available INTEGER NOT NULL DEFAULT 0,
                kiosk_information TEXT,
                public_information TEXT,
                organizer_phone TEXT,
                feedback_email TEXT,
                instagram_url TEXT,
                table_tiebreak TEXT NOT NULL DEFAULT 'Målskillnad först',
                playoff_tie_rule TEXT NOT NULL DEFAULT 'Straffar direkt',
                extra_time_minutes INTEGER NOT NULL DEFAULT 0,
                playoff_model_confirmed INTEGER NOT NULL DEFAULT 0,
                schedule_dirty INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament_id INTEGER REFERENCES tournaments(id) ON DELETE CASCADE,
                created_at TEXT NOT NULL,
                area TEXT NOT NULL,
                message TEXT NOT NULL,
                contact TEXT
            );
            CREATE TABLE IF NOT EXISTS offers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                business_name TEXT,
                description TEXT,
                discount_code TEXT,
                valid_until TEXT,
                url TEXT,
                active INTEGER NOT NULL DEFAULT 1,
                sort_order INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS sponsors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                level TEXT,
                description TEXT,
                website_url TEXT,
                logo_data_uri TEXT,
                active INTEGER NOT NULL DEFAULT 1,
                sort_order INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS functionaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                role TEXT NOT NULL,
                phone TEXT,
                email TEXT,
                pitch_number INTEGER,
                notes TEXT,
                public_contact INTEGER NOT NULL DEFAULT 0,
                active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS visitor_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
                session_token TEXT NOT NULL,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                view_count INTEGER NOT NULL DEFAULT 1,
                device_type TEXT NOT NULL DEFAULT 'Dator',
                browser TEXT NOT NULL DEFAULT 'Övrig',
                source TEXT NOT NULL DEFAULT 'Direkt / okänd',
                UNIQUE(tournament_id, session_token)
            );
            CREATE TABLE IF NOT EXISTS groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
                name TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS teams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                primary_color TEXT NOT NULL DEFAULT '#111827',
                secondary_color TEXT NOT NULL DEFAULT '#FFFFFF',
                home_pattern TEXT NOT NULL DEFAULT 'Helfärgad',
                home_color_2 TEXT NOT NULL DEFAULT '#FFFFFF',
                away_pattern TEXT NOT NULL DEFAULT 'Helfärgad',
                away_color_2 TEXT NOT NULL DEFAULT '#111827',
                group_id INTEGER REFERENCES groups(id) ON DELETE SET NULL,
                distance_km INTEGER NOT NULL DEFAULT 0,
                late_first_match INTEGER NOT NULL DEFAULT 0,
                earliest_first_time TEXT,
                travel_note TEXT
            );
            CREATE TABLE IF NOT EXISTS players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
                player_number INTEGER,
                name TEXT NOT NULL,
                birth_year INTEGER,
                position TEXT
            );
            CREATE TABLE IF NOT EXISTS referees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                phone TEXT,
                email TEXT,
                referee_level TEXT
            );
            CREATE TABLE IF NOT EXISTS brackets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                size INTEGER NOT NULL,
                bronze_match INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
                group_id INTEGER REFERENCES groups(id) ON DELETE CASCADE,
                bracket_id INTEGER REFERENCES brackets(id) ON DELETE CASCADE,
                stage TEXT NOT NULL,
                round_no INTEGER NOT NULL DEFAULT 1,
                match_no INTEGER NOT NULL DEFAULT 1,
                home_source TEXT NOT NULL,
                away_source TEXT NOT NULL,
                home_score INTEGER,
                away_score INTEGER,
                home_penalties INTEGER,
                away_penalties INTEGER,
                referee_id INTEGER REFERENCES referees(id) ON DELETE SET NULL,
                schedule_published INTEGER NOT NULL DEFAULT 0,
                schedule_locked INTEGER NOT NULL DEFAULT 0,
                decided_winner_id INTEGER REFERENCES teams(id) ON DELETE SET NULL
            );
            CREATE TABLE IF NOT EXISTS player_match_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
                player_id INTEGER NOT NULL REFERENCES players(id) ON DELETE CASCADE,
                goals INTEGER NOT NULL DEFAULT 0,
                assists INTEGER NOT NULL DEFAULT 0,
                yellow_cards INTEGER NOT NULL DEFAULT 0,
                red_cards INTEGER NOT NULL DEFAULT 0,
                UNIQUE(match_id, player_id)
            );
            CREATE TABLE IF NOT EXISTS schedule_rules (
                tournament_id INTEGER PRIMARY KEY REFERENCES tournaments(id) ON DELETE CASCADE,
                first_match_time TEXT NOT NULL DEFAULT '09:00',
                halves INTEGER NOT NULL DEFAULT 2,
                minutes_per_half INTEGER NOT NULL DEFAULT 20,
                halftime_minutes INTEGER NOT NULL DEFAULT 5,
                pitch_break_minutes INTEGER NOT NULL DEFAULT 5,
                minimum_team_rest_minutes INTEGER NOT NULL DEFAULT 45,
                avoid_consecutive_matches INTEGER NOT NULL DEFAULT 1,
                consecutive_match_break_minutes INTEGER NOT NULL DEFAULT 15,
                pitch_count INTEGER NOT NULL DEFAULT 2,
                referee_mode TEXT NOT NULL DEFAULT 'Automatisk',
                latest_kickoff_time TEXT NOT NULL DEFAULT '18:00'
            );
            DROP TRIGGER IF EXISTS prevent_team_limit_overflow;
            CREATE TRIGGER prevent_team_limit_overflow
            BEFORE INSERT ON teams
            FOR EACH ROW
            WHEN (
                SELECT COALESCE(expected_team_count, 0)
                FROM tournaments
                WHERE id = NEW.tournament_id
            ) > 0
            AND (
                SELECT COUNT(*)
                FROM teams
                WHERE tournament_id = NEW.tournament_id
            ) >= (
                SELECT expected_team_count
                FROM tournaments
                WHERE id = NEW.tournament_id
            )
            BEGIN
                SELECT RAISE(ABORT, 'TEAM_LIMIT_REACHED');
            END;
            """
        )
    # Uppgradera databasen från den tidigare versionen utan att radera data.
    team_cols = columns("teams")
    tournament_cols = columns("tournaments")
    match_cols = columns("matches")
    stat_cols = columns("player_match_stats")
    with db() as con:
        if "playoff_format" not in tournament_cols:
            con.execute("ALTER TABLE tournaments ADD COLUMN playoff_format TEXT NOT NULL DEFAULT 'Inget slutspel'")
        if "start_date" not in tournament_cols:
            con.execute("ALTER TABLE tournaments ADD COLUMN start_date TEXT")
        if "end_date" not in tournament_cols:
            con.execute("ALTER TABLE tournaments ADD COLUMN end_date TEXT")
        if "expected_team_count" not in tournament_cols:
            con.execute("ALTER TABLE tournaments ADD COLUMN expected_team_count INTEGER NOT NULL DEFAULT 0")
        if "is_published" not in tournament_cols:
            con.execute("ALTER TABLE tournaments ADD COLUMN is_published INTEGER NOT NULL DEFAULT 0")
        if "bronze_match" not in tournament_cols:
            con.execute("ALTER TABLE tournaments ADD COLUMN bronze_match INTEGER NOT NULL DEFAULT 0")
        if "arena_address" not in tournament_cols:
            con.execute("ALTER TABLE tournaments ADD COLUMN arena_address TEXT")
        if "kiosk_available" not in tournament_cols:
            con.execute("ALTER TABLE tournaments ADD COLUMN kiosk_available INTEGER NOT NULL DEFAULT 0")
        if "kiosk_information" not in tournament_cols:
            con.execute("ALTER TABLE tournaments ADD COLUMN kiosk_information TEXT")
        if "public_information" not in tournament_cols:
            con.execute("ALTER TABLE tournaments ADD COLUMN public_information TEXT")
        if "organizer_phone" not in tournament_cols:
            con.execute("ALTER TABLE tournaments ADD COLUMN organizer_phone TEXT")
        if "feedback_email" not in tournament_cols:
            con.execute("ALTER TABLE tournaments ADD COLUMN feedback_email TEXT")
        if "instagram_url" not in tournament_cols:
            con.execute("ALTER TABLE tournaments ADD COLUMN instagram_url TEXT")
        if "table_tiebreak" not in tournament_cols:
            con.execute("ALTER TABLE tournaments ADD COLUMN table_tiebreak TEXT NOT NULL DEFAULT 'Målskillnad först'")
        if "playoff_tie_rule" not in tournament_cols:
            con.execute("ALTER TABLE tournaments ADD COLUMN playoff_tie_rule TEXT NOT NULL DEFAULT 'Straffar direkt'")
        if "extra_time_minutes" not in tournament_cols:
            con.execute("ALTER TABLE tournaments ADD COLUMN extra_time_minutes INTEGER NOT NULL DEFAULT 0")
        if "playoff_model_confirmed" not in tournament_cols:
            con.execute("ALTER TABLE tournaments ADD COLUMN playoff_model_confirmed INTEGER NOT NULL DEFAULT 0")
        if "schedule_dirty" not in tournament_cols:
            con.execute("ALTER TABLE tournaments ADD COLUMN schedule_dirty INTEGER NOT NULL DEFAULT 1")
        con.execute(
            "UPDATE tournaments SET playoff_format=? WHERE playoff_format=?",
            ("Placeringsslutspel – ettor mot ettor osv.", "Flera egna slutspel"),
        )
        con.execute(
            "UPDATE tournaments SET playoff_format='Inget slutspel' WHERE playoff_format='Ett gemensamt slutspel'"
        )
        if "group_id" not in team_cols:
            con.execute("ALTER TABLE teams ADD COLUMN group_id INTEGER REFERENCES groups(id) ON DELETE SET NULL")
        if "primary_color" not in team_cols:
            con.execute("ALTER TABLE teams ADD COLUMN primary_color TEXT NOT NULL DEFAULT '#111827'")
        if "secondary_color" not in team_cols:
            con.execute("ALTER TABLE teams ADD COLUMN secondary_color TEXT NOT NULL DEFAULT '#FFFFFF'")
        if "home_pattern" not in team_cols:
            con.execute("ALTER TABLE teams ADD COLUMN home_pattern TEXT NOT NULL DEFAULT 'Helfärgad'")
        if "home_color_2" not in team_cols:
            con.execute("ALTER TABLE teams ADD COLUMN home_color_2 TEXT NOT NULL DEFAULT '#FFFFFF'")
        if "away_pattern" not in team_cols:
            con.execute("ALTER TABLE teams ADD COLUMN away_pattern TEXT NOT NULL DEFAULT 'Helfärgad'")
        if "away_color_2" not in team_cols:
            con.execute("ALTER TABLE teams ADD COLUMN away_color_2 TEXT NOT NULL DEFAULT '#111827'")
        if "distance_km" not in team_cols:
            con.execute("ALTER TABLE teams ADD COLUMN distance_km INTEGER NOT NULL DEFAULT 0")
        if "late_first_match" not in team_cols:
            con.execute("ALTER TABLE teams ADD COLUMN late_first_match INTEGER NOT NULL DEFAULT 0")
        if "earliest_first_time" not in team_cols:
            con.execute("ALTER TABLE teams ADD COLUMN earliest_first_time TEXT")
        if "travel_note" not in team_cols:
            con.execute("ALTER TABLE teams ADD COLUMN travel_note TEXT")
        if "scheduled_start" not in match_cols:
            con.execute("ALTER TABLE matches ADD COLUMN scheduled_start TEXT")
        if "pitch_number" not in match_cols:
            con.execute("ALTER TABLE matches ADD COLUMN pitch_number INTEGER")
        if "schedule_published" not in match_cols:
            con.execute("ALTER TABLE matches ADD COLUMN schedule_published INTEGER NOT NULL DEFAULT 0")
        if "schedule_locked" not in match_cols:
            con.execute("ALTER TABLE matches ADD COLUMN schedule_locked INTEGER NOT NULL DEFAULT 0")
        if "decided_winner_id" not in match_cols:
            con.execute("ALTER TABLE matches ADD COLUMN decided_winner_id INTEGER REFERENCES teams(id) ON DELETE SET NULL")
        if "yellow_cards" not in stat_cols:
            con.execute("ALTER TABLE player_match_stats ADD COLUMN yellow_cards INTEGER NOT NULL DEFAULT 0")
        if "red_cards" not in stat_cols:
            con.execute("ALTER TABLE player_match_stats ADD COLUMN red_cards INTEGER NOT NULL DEFAULT 0")
        rule_cols = columns("schedule_rules")
        if "latest_kickoff_time" not in rule_cols:
            con.execute("ALTER TABLE schedule_rules ADD COLUMN latest_kickoff_time TEXT NOT NULL DEFAULT '18:00'")
        if "avoid_consecutive_matches" not in rule_cols:
            con.execute("ALTER TABLE schedule_rules ADD COLUMN avoid_consecutive_matches INTEGER NOT NULL DEFAULT 1")
        if "consecutive_match_break_minutes" not in rule_cols:
            con.execute("ALTER TABLE schedule_rules ADD COLUMN consecutive_match_break_minutes INTEGER NOT NULL DEFAULT 15")
        con.execute("UPDATE tournaments SET start_date=COALESCE(start_date,tournament_date), end_date=COALESCE(end_date,tournament_date)")
        # Ändringar som påverkar schemaförutsättningarna markerar automatiskt schemat som inaktuellt.
        execute_script(con, """
            DROP TRIGGER IF EXISTS cupnavi_dirty_team_insert;
            DROP TRIGGER IF EXISTS cupnavi_dirty_team_update;
            DROP TRIGGER IF EXISTS cupnavi_dirty_team_delete;
            DROP TRIGGER IF EXISTS cupnavi_dirty_group_insert;
            DROP TRIGGER IF EXISTS cupnavi_dirty_group_update;
            DROP TRIGGER IF EXISTS cupnavi_dirty_group_delete;
            DROP TRIGGER IF EXISTS cupnavi_dirty_ref_insert;
            DROP TRIGGER IF EXISTS cupnavi_dirty_ref_update;
            DROP TRIGGER IF EXISTS cupnavi_dirty_ref_delete;
            DROP TRIGGER IF EXISTS cupnavi_dirty_rules_update;
            DROP TRIGGER IF EXISTS cupnavi_dirty_tournament_rules;

            CREATE TRIGGER cupnavi_dirty_team_insert AFTER INSERT ON teams
            BEGIN UPDATE tournaments SET schedule_dirty=1 WHERE id=NEW.tournament_id; END;
            CREATE TRIGGER cupnavi_dirty_team_update AFTER UPDATE OF group_id,distance_km,late_first_match,earliest_first_time ON teams
            WHEN OLD.group_id IS NOT NEW.group_id
              OR OLD.distance_km IS NOT NEW.distance_km
              OR OLD.late_first_match IS NOT NEW.late_first_match
              OR OLD.earliest_first_time IS NOT NEW.earliest_first_time
            BEGIN UPDATE tournaments SET schedule_dirty=1 WHERE id=NEW.tournament_id; END;
            CREATE TRIGGER cupnavi_dirty_team_delete AFTER DELETE ON teams
            BEGIN UPDATE tournaments SET schedule_dirty=1 WHERE id=OLD.tournament_id; END;

            CREATE TRIGGER cupnavi_dirty_group_insert AFTER INSERT ON groups
            BEGIN UPDATE tournaments SET schedule_dirty=1 WHERE id=NEW.tournament_id; END;
            CREATE TRIGGER cupnavi_dirty_group_update AFTER UPDATE OF name ON groups
            BEGIN UPDATE tournaments SET schedule_dirty=1 WHERE id=NEW.tournament_id; END;
            CREATE TRIGGER cupnavi_dirty_group_delete AFTER DELETE ON groups
            BEGIN UPDATE tournaments SET schedule_dirty=1 WHERE id=OLD.tournament_id; END;

            CREATE TRIGGER cupnavi_dirty_ref_insert AFTER INSERT ON referees
            BEGIN UPDATE tournaments SET schedule_dirty=1 WHERE id=NEW.tournament_id; END;
            CREATE TRIGGER cupnavi_dirty_ref_delete AFTER DELETE ON referees
            BEGIN UPDATE tournaments SET schedule_dirty=1 WHERE id=OLD.tournament_id; END;

            CREATE TRIGGER cupnavi_dirty_rules_update AFTER UPDATE ON schedule_rules
            WHEN OLD.first_match_time IS NOT NEW.first_match_time
              OR OLD.halves IS NOT NEW.halves
              OR OLD.minutes_per_half IS NOT NEW.minutes_per_half
              OR OLD.halftime_minutes IS NOT NEW.halftime_minutes
              OR OLD.pitch_break_minutes IS NOT NEW.pitch_break_minutes
              OR OLD.minimum_team_rest_minutes IS NOT NEW.minimum_team_rest_minutes
              OR OLD.avoid_consecutive_matches IS NOT NEW.avoid_consecutive_matches
              OR OLD.consecutive_match_break_minutes IS NOT NEW.consecutive_match_break_minutes
              OR OLD.pitch_count IS NOT NEW.pitch_count
              OR OLD.referee_mode IS NOT NEW.referee_mode
              OR OLD.latest_kickoff_time IS NOT NEW.latest_kickoff_time
            BEGIN UPDATE tournaments SET schedule_dirty=1 WHERE id=NEW.tournament_id; END;

            CREATE TRIGGER cupnavi_dirty_tournament_rules
            AFTER UPDATE OF start_date,end_date,playoff_format,bronze_match,playoff_tie_rule,extra_time_minutes ON tournaments
            WHEN OLD.start_date IS NOT NEW.start_date
              OR OLD.end_date IS NOT NEW.end_date
              OR OLD.playoff_format IS NOT NEW.playoff_format
              OR OLD.bronze_match IS NOT NEW.bronze_match
              OR OLD.playoff_tie_rule IS NOT NEW.playoff_tie_rule
              OR OLD.extra_time_minutes IS NOT NEW.extra_time_minutes
            BEGIN UPDATE tournaments SET schedule_dirty=1 WHERE id=NEW.id; END;
        """)
        # V96+ måste även tåla blandade releasefiler i drift. Säkerställ därför
        # erfarenhets-/multisportschemat innan den versionsstyrda migreringen körs.
        ensure_v96_experience_schema_compat(con)
        ensure_v99_team_portal_schema_compat(con)
        ensure_v106_participant_privacy_schema_compat(con)
        ensure_v100_international_schema_compat(con)
        ensure_v102_lifecycle_schema_compat(con)

        # Från och med Stabilisering 1.0 registreras schemaändringar versionsstyrt.
        # Den äldre bootstrap-koden ovan behålls tills alla tidigare installationer
        # har migrerats säkert till den nya modellen.
        apply_migrations(con)
        con.commit()
    return schema_key


# Cache endast under ett enskilt Streamlit-renderingsvarv. Den återställs vid rerun,
# så administratören ser alltid nya data efter en skrivning utan långlivad cache.
_RENDER_QUERY_CACHE = {}
_PERF = {"db_calls": 0, "db_ms": 0.0, "cache_hits": 0, "writes": 0}

def _record_db_call(started, write=False):
    _PERF["db_calls"] += 1
    _PERF["db_ms"] += (time.perf_counter() - started) * 1000
    if write:
        _PERF["writes"] += 1

def _cacheable_query(sql):
    return sql.lstrip().upper().startswith(("SELECT", "PRAGMA"))

def _query_cache_key(kind, sql, params):
    try:
        frozen_params = tuple(params)
        hash(frozen_params)
    except Exception:
        return None
    return (kind, sql, frozen_params)

def _clear_render_query_cache():
    _RENDER_QUERY_CACHE.clear()

def all_rows(sql, params=()):
    key = _query_cache_key("all", sql, params) if _cacheable_query(sql) else None
    if key is not None and key in _RENDER_QUERY_CACHE:
        _PERF["cache_hits"] += 1
        return _RENDER_QUERY_CACHE[key]
    started = time.perf_counter()
    with db() as con:
        result = _rows_from_cursor(con.execute(sql, params))
    _record_db_call(started)
    if key is not None:
        _RENDER_QUERY_CACHE[key] = result
    return result


def one_row(sql, params=()):
    key = _query_cache_key("one", sql, params) if _cacheable_query(sql) else None
    if key is not None and key in _RENDER_QUERY_CACHE:
        _PERF["cache_hits"] += 1
        return _RENDER_QUERY_CACHE[key]
    started = time.perf_counter()
    with db() as con:
        result = _one_from_cursor(con.execute(sql, params))
    _record_db_call(started)
    if key is not None:
        _RENDER_QUERY_CACHE[key] = result
    return result


def run(sql, params=()):
    _clear_render_query_cache()
    started = time.perf_counter()
    with db() as con:
        cur = con.execute(sql, params)
        con.commit()
        lastrowid = cur.lastrowid
    _record_db_call(started, write=True)
    return lastrowid


def _json_snapshot(value):
    try:
        return json.dumps(value, ensure_ascii=False, default=str, sort_keys=True)
    except Exception:
        return None


def record_audit(tournament_id, action_type, entity_type, description, *, entity_id=None,
                 before=None, after=None, reversible=False, actor="Admin"):
    """Spara en kompakt ändringspost för nya CupNavi-verktyg."""
    return run(
        """INSERT INTO audit_log(
               tournament_id,created_at,actor,action_type,entity_type,entity_id,description,
               before_json,after_json,reversible
           ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
        (tournament_id, datetime.now().isoformat(timespec="seconds"), actor, action_type,
         entity_type, entity_id, description, _json_snapshot(before), _json_snapshot(after),
         1 if reversible else 0),
    )


def add_feed_item(tournament_id, title, detail=None, *, category="Info", related_match_id=None, public=True):
    return run(
        """INSERT INTO cup_feed(tournament_id,created_at,category,title,detail,public,related_match_id)
           VALUES(?,?,?,?,?,?,?)""",
        (tournament_id, datetime.now().isoformat(timespec="seconds"), category, title, detail,
         1 if public else 0, related_match_id),
    )


def add_team_notification(tournament_id, team_id, title, message, event_key=None):
    """Skapa en idempotent lagnotis. Dubbletter med samma event_key ignoreras."""
    try:
        return run(
            """INSERT INTO notifications(tournament_id,team_id,created_at,title,message,event_key)
               VALUES(?,?,?,?,?,?)""",
            (tournament_id, team_id, datetime.now().isoformat(timespec="seconds"), title, message, event_key),
        )
    except Exception as exc:
        if "UNIQUE" in str(exc).upper():
            return None
        raise


def _match_team_ids(match_row):
    ids = []
    for source in (match_row["home_source"], match_row["away_source"]):
        resolved = resolve_source(source)
        if resolved:
            ids.append(int(resolved))
    return ids


def schedule_repository():
    """Repository-gräns för all SQL som hör till schemadomänen."""
    return ScheduleRepository(
        fetch_all=all_rows,
        connection_factory=db,
        clear_cache=_clear_render_query_cache,
    )


class TeamLimitReachedError(Exception):
    pass


def insert_team_with_limit(tournament_id, name, primary_color, secondary_color,
                           home_pattern, home_color_2, away_pattern, away_color_2,
                           distance_km, late_first_match, earliest_first_time, travel_note):
    """Lägg till ett lag atomiskt och respektera alltid turneringens sparade maxantal."""
    con = db()
    try:
        # Lokalt låser BEGIN IMMEDIATE bort samtidiga SQLite-skrivningar.
        # I Turso är triggern den slutliga atomiska spärren på serversidan.
        if not CLOUD_DATABASE_ENABLED:
            con.execute("BEGIN IMMEDIATE")
        tournament_row = _one_from_cursor(con.execute(
            "SELECT COALESCE(expected_team_count, 0) AS max_teams FROM tournaments WHERE id=?",
            (tournament_id,),
        ))
        if tournament_row is None:
            raise ValueError("Turneringen finns inte längre.")
        max_teams = int(tournament_row["max_teams"] or 0)
        current_count_row = _one_from_cursor(con.execute(
            "SELECT COUNT(*) AS n FROM teams WHERE tournament_id=?", (tournament_id,)
        ))
        current_count = int(current_count_row["n"])
        if max_teams > 0 and current_count >= max_teams:
            raise TeamLimitReachedError(max_teams)
        cur = con.execute(
            """INSERT INTO teams(
                tournament_id,name,group_id,primary_color,secondary_color,
                home_pattern,home_color_2,away_pattern,away_color_2,
                distance_km,late_first_match,earliest_first_time,travel_note
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (tournament_id, name, None, primary_color, secondary_color,
             home_pattern, home_color_2, away_pattern, away_color_2,
             distance_km, int(late_first_match), earliest_first_time, travel_note),
        )
        con.commit()
        return cur.lastrowid
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def team(team_id):
    return one_row("SELECT * FROM teams WHERE id=?", (team_id,)) if team_id else None


def calculate_table(group_id, tournament):
    teams = all_rows("SELECT * FROM teams WHERE group_id=? ORDER BY name", (group_id,))
    stats = {
        t["id"]: {"Lag": t["name"], "S": 0, "V": 0, "O": 0, "F": 0, "GM": 0, "IM": 0, "MS": 0, "P": 0}
        for t in teams
    }
    matches = all_rows(
        "SELECT * FROM matches WHERE group_id=? AND stage='Gruppspel' AND home_score IS NOT NULL AND away_score IS NOT NULL",
        (group_id,),
    )
    for m in matches:
        h = int(m["home_source"].split(":")[1])
        a = int(m["away_source"].split(":")[1])
        if h not in stats or a not in stats:
            continue
        hs, aas = int(m["home_score"]), int(m["away_score"])
        stats[h]["S"] += 1; stats[a]["S"] += 1
        stats[h]["GM"] += hs; stats[h]["IM"] += aas
        stats[a]["GM"] += aas; stats[a]["IM"] += hs
        if hs > aas:
            stats[h]["V"] += 1; stats[a]["F"] += 1
            stats[h]["P"] += tournament["points_win"]; stats[a]["P"] += tournament["points_loss"]
        elif hs < aas:
            stats[a]["V"] += 1; stats[h]["F"] += 1
            stats[a]["P"] += tournament["points_win"]; stats[h]["P"] += tournament["points_loss"]
        else:
            stats[h]["O"] += 1; stats[a]["O"] += 1
            stats[h]["P"] += tournament["points_draw"]; stats[a]["P"] += tournament["points_draw"]
    for row in stats.values():
        row["MS"] = row["GM"] - row["IM"]

    tiebreak = tournament.get("table_tiebreak", "Målskillnad först") if hasattr(tournament, "get") else tournament["table_tiebreak"]
    if not tiebreak:
        tiebreak = "Målskillnad först"

    # Grundsortering på poäng. Vid lika poäng kan användaren välja om målskillnad
    # eller inbördes möten ska väga tyngst.
    point_groups = {}
    for team_id, data in stats.items():
        point_groups.setdefault(data["P"], []).append(team_id)

    ordered_ids = []
    for points in sorted(point_groups.keys(), reverse=True):
        tied_ids = point_groups[points]
        if len(tied_ids) == 1:
            ordered_ids.extend(tied_ids)
            continue

        if tiebreak == "Inbördes möten först":
            h2h = {team_id: {"P": 0, "MS": 0, "GM": 0} for team_id in tied_ids}
            tied_set = set(tied_ids)
            for m in matches:
                h = int(m["home_source"].split(":")[1])
                a = int(m["away_source"].split(":")[1])
                if h not in tied_set or a not in tied_set:
                    continue
                hs, aas = int(m["home_score"]), int(m["away_score"])
                h2h[h]["GM"] += hs; h2h[h]["MS"] += hs - aas
                h2h[a]["GM"] += aas; h2h[a]["MS"] += aas - hs
                if hs > aas:
                    h2h[h]["P"] += tournament["points_win"]; h2h[a]["P"] += tournament["points_loss"]
                elif hs < aas:
                    h2h[a]["P"] += tournament["points_win"]; h2h[h]["P"] += tournament["points_loss"]
                else:
                    h2h[h]["P"] += tournament["points_draw"]; h2h[a]["P"] += tournament["points_draw"]
            tied_ids.sort(
                key=lambda team_id: (
                    -h2h[team_id]["P"], -h2h[team_id]["MS"], -h2h[team_id]["GM"],
                    -stats[team_id]["MS"], -stats[team_id]["GM"], stats[team_id]["Lag"].lower()
                )
            )
        else:
            tied_ids.sort(key=lambda team_id: (-stats[team_id]["MS"], -stats[team_id]["GM"], stats[team_id]["Lag"].lower()))
        ordered_ids.extend(tied_ids)

    return [(team_id, stats[team_id]) for team_id in ordered_ids]


def result_winner(match_row, want_loser=False):
    home_id = resolve_source(match_row["home_source"])
    away_id = resolve_source(match_row["away_source"])
    if not home_id or not away_id or match_row["home_score"] is None or match_row["away_score"] is None:
        return None
    hs, aas = match_row["home_score"], match_row["away_score"]
    if hs == aas:
        decided = match_row["decided_winner_id"] if "decided_winner_id" in match_row else None
        if decided in (home_id, away_id):
            winner = decided
            loser = away_id if winner == home_id else home_id
        else:
            hp, ap = match_row["home_penalties"], match_row["away_penalties"]
            if hp is None or ap is None or hp == ap:
                return None
            winner, loser = (home_id, away_id) if hp > ap else (away_id, home_id)
    else:
        winner, loser = (home_id, away_id) if hs > aas else (away_id, home_id)
    return loser if want_loser else winner


def group_table_is_final(group_id):
    """En gruppplacering får inte lösas till ett lag förrän hela gruppspelet är klart."""
    team_count = one_row("SELECT COUNT(*) AS n FROM teams WHERE group_id=?", (group_id,))["n"]
    expected_matches = team_count * (team_count - 1) // 2
    if expected_matches == 0:
        return False
    completed_matches = one_row(
        """SELECT COUNT(*) AS n FROM matches
        WHERE group_id=? AND stage='Gruppspel' AND home_score IS NOT NULL AND away_score IS NOT NULL""",
        (group_id,),
    )["n"]
    return completed_matches >= expected_matches


def resolve_source(source):
    if not source:
        return None
    parts = source.split(":")
    if parts[0] == "team":
        return int(parts[1])
    if parts[0] == "group":
        group_id, rank = int(parts[1]), int(parts[2])
        if not group_table_is_final(group_id):
            return None
        tournament_id = one_row("SELECT tournament_id FROM groups WHERE id=?", (group_id,))["tournament_id"]
        tournament = one_row("SELECT * FROM tournaments WHERE id=?", (tournament_id,))
        table = calculate_table(group_id, tournament)
        return table[rank - 1][0] if 0 < rank <= len(table) else None
    if parts[0] in ("winner", "loser"):
        match_row = one_row("SELECT * FROM matches WHERE id=?", (int(parts[1]),))
        return result_winner(match_row, want_loser=parts[0] == "loser") if match_row else None
    return None


def source_label(source):
    team_id = resolve_source(source)
    if team_id:
        selected = team(team_id)
        return selected["name"] if selected else "Okänt lag"
    parts = source.split(":") if source else []
    if parts and parts[0] == "group":
        group = one_row("SELECT name FROM groups WHERE id=?", (int(parts[1]),))
        if not group:
            return "Gruppplacering"
        rank = int(parts[2])
        return f"Vinnaren i {group['name']}" if rank == 1 else f"{rank}:an i {group['name']}"
    if parts and parts[0] == "winner":
        source_match = one_row("SELECT * FROM matches WHERE id=?", (int(parts[1]),))
        if source_match:
            schedule_text, _ = match_meta(source_match)
            match_name = schedule_text.split(" · ", 1)[0]
            return f"Vinnare {match_name.lower()}"
        return "Vinnare i match"
    if parts and parts[0] == "loser":
        source_match = one_row("SELECT * FROM matches WHERE id=?", (int(parts[1]),))
        if source_match:
            schedule_text, _ = match_meta(source_match)
            match_name = schedule_text.split(" · ", 1)[0]
            return f"Förlorare {match_name.lower()}"
        return "Förlorare i match"
    return "Ej klart"


def match_meta(match_row):
    ordered = all_rows(
        "SELECT id FROM matches WHERE tournament_id=? AND scheduled_start IS NOT NULL ORDER BY scheduled_start,pitch_number,id",
        (match_row["tournament_id"],),
    )
    match_number = next((index for index, row in enumerate(ordered, 1) if row["id"] == match_row["id"]), None)
    referee = one_row("SELECT name FROM referees WHERE id=?", (match_row["referee_id"],)) if match_row["referee_id"] else None
    if match_row["scheduled_start"]:
        start = swedish_datetime(match_row["scheduled_start"])
        schedule_text = f"Match {match_number} · {start} · Plan {match_row['pitch_number']}"
    else:
        schedule_text = "Ej schemalagd"
    return schedule_text, referee["name"] if referee else "Ej tillsatt"


def match_result_label(match_row):
    schedule_text, referee = match_meta(match_row)
    return (
        f"{schedule_text} · {match_row['stage']}: "
        f"{source_label(match_row['home_source'])} {match_row['home_score']}–{match_row['away_score']} "
        f"{source_label(match_row['away_source'])} · Domare: {referee}"
    )


SWEDISH_WEEKDAYS = ["Måndag", "Tisdag", "Onsdag", "Torsdag", "Fredag", "Lördag", "Söndag"]
SWEDISH_MONTHS = ["januari", "februari", "mars", "april", "maj", "juni", "juli", "augusti", "september", "oktober", "november", "december"]


def swedish_datetime(value):
    moment = datetime.fromisoformat(value) if isinstance(value, str) else value
    return f"{SWEDISH_WEEKDAYS[moment.weekday()]} {moment.day} {SWEDISH_MONTHS[moment.month - 1]} {moment.year} · {moment.strftime('%H:%M')}"


def cup_date_label(tournament):
    start_text = tournament["start_date"] or tournament["tournament_date"]
    end_text = tournament["end_date"] or start_text
    if not start_text:
        return "Cupdatum saknas"
    start = datetime.fromisoformat(start_text)
    end = datetime.fromisoformat(end_text)
    if start.date() == end.date():
        return f"{SWEDISH_WEEKDAYS[start.weekday()]} {start.day} {SWEDISH_MONTHS[start.month - 1]} {start.year}"
    return f"{start.day} {SWEDISH_MONTHS[start.month - 1]} {start.year}–{end.day} {SWEDISH_MONTHS[end.month - 1]} {end.year}"


WEATHER_CODES = {
    0: ("☀️", "Klart"), 1: ("🌤️", "Mestadels klart"), 2: ("⛅", "Växlande molnighet"),
    3: ("☁️", "Mulet"), 45: ("🌫️", "Dimma"), 48: ("🌫️", "Rimfrost och dimma"),
    51: ("🌦️", "Lätt duggregn"), 53: ("🌦️", "Duggregn"), 55: ("🌧️", "Kraftigt duggregn"),
    56: ("🌧️", "Underkylt duggregn"), 57: ("🌧️", "Kraftigt underkylt duggregn"),
    61: ("🌦️", "Lätt regn"), 63: ("🌧️", "Regn"), 65: ("🌧️", "Kraftigt regn"),
    66: ("🌧️", "Underkylt regn"), 67: ("🌧️", "Kraftigt underkylt regn"),
    71: ("🌨️", "Lätt snöfall"), 73: ("🌨️", "Snöfall"), 75: ("❄️", "Kraftigt snöfall"),
    77: ("🌨️", "Snökorn"), 80: ("🌦️", "Lätta regnskurar"), 81: ("🌧️", "Regnskurar"),
    82: ("⛈️", "Kraftiga regnskurar"), 85: ("🌨️", "Lätta snöbyar"), 86: ("❄️", "Kraftiga snöbyar"),
    95: ("⛈️", "Åska"), 96: ("⛈️", "Åska med lätt hagel"), 99: ("⛈️", "Åska med kraftigt hagel"),
}


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_weather_forecast(place):
    """Hämta aktuell timprognos utan API-nyckel. Fel får aldrig stoppa Turneringsvyn."""
    if not place or not place.strip():
        return {}, "Spelort saknas"
    try:
        geocode_url = "https://geocoding-api.open-meteo.com/v1/search?" + urlencode({
            "name": place.strip(), "count": 1, "language": "sv", "format": "json",
        })
        request = Request(geocode_url, headers={"User-Agent": "Fotbollsturnering/1.0"})
        with urlopen(request, timeout=6) as response:
            geocode = json.load(response)
        results = geocode.get("results") or []
        if not results:
            return {}, f"Kunde inte hitta spelorten {place}."
        location = results[0]
        forecast_url = "https://api.open-meteo.com/v1/forecast?" + urlencode({
            "latitude": location["latitude"],
            "longitude": location["longitude"],
            "hourly": "temperature_2m,precipitation_probability,weather_code,wind_speed_10m",
            "forecast_days": 16,
            "timezone": "auto",
        })
        request = Request(forecast_url, headers={"User-Agent": "Fotbollsturnering/1.0"})
        with urlopen(request, timeout=8) as response:
            forecast = json.load(response)
        hourly = forecast.get("hourly") or {}
        times = hourly.get("time") or []
        values = {}
        for index, time_value in enumerate(times):
            values[time_value] = {
                "temperature": hourly.get("temperature_2m", [None] * len(times))[index],
                "rain_probability": hourly.get("precipitation_probability", [None] * len(times))[index],
                "weather_code": hourly.get("weather_code", [None] * len(times))[index],
                "wind_speed": hourly.get("wind_speed_10m", [None] * len(times))[index],
            }
        resolved_place = location.get("name", place)
        return {"place": resolved_place, "hours": values}, ""
    except Exception:
        return {}, "Väderprognosen kan inte hämtas just nu."


def weather_for_match(forecast, scheduled_start):
    if not forecast or not scheduled_start:
        return None
    moment = datetime.fromisoformat(scheduled_start)
    forecast_hour = moment.replace(minute=0, second=0, microsecond=0)
    if moment.minute >= 30:
        forecast_hour += timedelta(hours=1)
    return forecast.get("hours", {}).get(forecast_hour.strftime("%Y-%m-%dT%H:%M"))


def weather_label(weather):
    if not weather:
        return "Prognos tillgänglig närmare matchdagen"
    icon, description = WEATHER_CODES.get(weather.get("weather_code"), ("🌡️", "Väder"))
    temperature = "–" if weather.get("temperature") is None else f"{round(weather['temperature'])} °C"
    rain = "–" if weather.get("rain_probability") is None else f"{round(weather['rain_probability'])} % regnrisk"
    wind = "–" if weather.get("wind_speed") is None else f"{round(weather['wind_speed'])} km/h vind"
    return f"{icon} {description} · {temperature} · {rain} · {wind}"


def _row_value(row, key, default=None):
    """Läs ett fält säkert från sqlite/libsql-rader, dictar och äldre schema."""
    if not row:
        return default
    try:
        value = row[key]
    except (KeyError, IndexError, TypeError):
        value = default
    except Exception:
        value = default
    return default if value is None else value


def _team_value(team_row, key, default=None):
    """Bakåtkompatibel wrapper för lagrader."""
    return _row_value(team_row, key, default)


KIT_PATTERNS = ["Helfärgad", "Vertikala ränder", "Horisontella ränder", "Rutigt", "Delad"]


def kit_colors(team_row, kit="home"):
    """Returnera de färger som faktiskt syns i ett hemma- eller bortaställ."""
    if not team_row:
        return ["#9CA3AF"]
    if kit == "away":
        pattern = _team_value(team_row, "away_pattern", "Helfärgad")
        color_1 = _team_value(team_row, "secondary_color", "#FFFFFF")
        color_2 = _team_value(team_row, "away_color_2", "#111827")
    else:
        pattern = _team_value(team_row, "home_pattern", "Helfärgad")
        color_1 = _team_value(team_row, "primary_color", "#111827")
        color_2 = _team_value(team_row, "home_color_2", "#FFFFFF")
    return [color_1] if pattern == "Helfärgad" else [color_1, color_2]


def kit_pattern(team_row, kit="home"):
    if kit == "away":
        return _team_value(team_row, "away_pattern", "Helfärgad")
    return _team_value(team_row, "home_pattern", "Helfärgad")


def kit_background(pattern, color_1, color_2):
    """CSS-bakgrund som visuellt återger valt tröjmönster."""
    if pattern == "Vertikala ränder":
        return f"repeating-linear-gradient(90deg,{color_1} 0 8px,{color_2} 8px 16px)"
    if pattern == "Horisontella ränder":
        return f"repeating-linear-gradient(0deg,{color_1} 0 7px,{color_2} 7px 14px)"
    if pattern == "Rutigt":
        return f"conic-gradient({color_1} 25%,{color_2} 0 50%,{color_1} 0 75%,{color_2} 0) 0 0/16px 16px"
    if pattern == "Delad":
        return f"linear-gradient(90deg,{color_1} 0 50%,{color_2} 50% 100%)"
    return color_1


def kit_background_for_team(team_row, kit="home"):
    colors = kit_colors(team_row, kit)
    color_1 = colors[0]
    color_2 = colors[1] if len(colors) > 1 else color_1
    return kit_background(kit_pattern(team_row, kit), color_1, color_2)


def kit_preview_html(pattern, color_1, color_2, title):
    bg = kit_background(pattern, color_1, color_2)
    return (
        f"<div style='display:flex;align-items:center;gap:10px;margin:4px 0 10px'>"
        f"<span style='width:58px;height:32px;border:1px solid #64748b;border-radius:7px;background:{bg};display:inline-block'></span>"
        f"<span style='color:#334155;font-size:13px'><b>{html.escape(title)}</b><br>{html.escape(pattern)}</span></div>"
    )


def kit_swatch(team_row, kit="home"):
    """SVG-ruta för Streamlit-tabeller som kan visa två färger och mönster."""
    colors = kit_colors(team_row, kit)
    c1 = colors[0]
    c2 = colors[1] if len(colors) > 1 else c1
    pattern = kit_pattern(team_row, kit)
    defs = ""
    fill = c1
    if pattern == "Vertikala ränder":
        defs = f"<pattern id='p' width='12' height='24' patternUnits='userSpaceOnUse'><rect width='6' height='24' fill='{c1}'/><rect x='6' width='6' height='24' fill='{c2}'/></pattern>"
        fill = "url(#p)"
    elif pattern == "Horisontella ränder":
        defs = f"<pattern id='p' width='58' height='12' patternUnits='userSpaceOnUse'><rect width='58' height='6' fill='{c1}'/><rect y='6' width='58' height='6' fill='{c2}'/></pattern>"
        fill = "url(#p)"
    elif pattern == "Rutigt":
        defs = f"<pattern id='p' width='12' height='12' patternUnits='userSpaceOnUse'><rect width='12' height='12' fill='{c1}'/><rect width='6' height='6' fill='{c2}'/><rect x='6' y='6' width='6' height='6' fill='{c2}'/></pattern>"
        fill = "url(#p)"
    elif pattern == "Delad":
        defs = f"<linearGradient id='p' x1='0' x2='1'><stop offset='50%' stop-color='{c1}'/><stop offset='50%' stop-color='{c2}'/></linearGradient>"
        fill = "url(#p)"
    svg = f"<svg xmlns='http://www.w3.org/2000/svg' width='58' height='24' viewBox='0 0 58 24'><defs>{defs}</defs><rect x='1' y='1' width='56' height='22' rx='4' fill='{fill}' stroke='#475569'/></svg>"
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("ascii")


def _hex_rgb(value):
    value = (value or "").strip().lstrip("#")
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    if len(value) != 6:
        return None
    try:
        return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return None


def colors_similar(color_a, color_b, threshold=72):
    """Praktisk färgkrock: fånga även tydligt närliggande nyanser, inte bara identiska hexvärden."""
    a, b = _hex_rgb(color_a), _hex_rgb(color_b)
    if not a or not b:
        return str(color_a).casefold() == str(color_b).casefold()
    distance = sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5
    return distance <= threshold


def kits_conflict(team_a, kit_a, team_b, kit_b):
    return any(colors_similar(a, b) for a in kit_colors(team_a, kit_a) for b in kit_colors(team_b, kit_b))


def match_kit_colors(home_team, away_team):
    """Behåll kompatibel returtyp men välj bortaställ utifrån alla synliga färger."""
    if not home_team or not away_team:
        return "#9CA3AF", "#FFFFFF", False
    use_away_kit = kits_conflict(home_team, "home", away_team, "home")
    home_color = kit_colors(home_team, "home")[0]
    away_color = kit_colors(away_team, "away" if use_away_kit else "home")[0]
    return home_color, away_color, use_away_kit


def kit_color_conflict(home_team, away_team):
    """Kontrollera om bortalagets valda ställ fortfarande krockar med hemmastället."""
    if not home_team or not away_team:
        return False
    use_away_kit = kits_conflict(home_team, "home", away_team, "home")
    selected_away_kit = "away" if use_away_kit else "home"
    return kits_conflict(home_team, "home", away_team, selected_away_kit)


def optimize_group_home_away(tournament_id):
    """
    Optimera hemma/borta i gruppspelet.

    Prioritet 1: välj den riktning som undviker färgkrock när endast en riktning gör det.
    Prioritet 2: bland färgmässigt likvärdiga riktningar, jämna ut hemma/borta per lag.
    Matcher med registrerat resultat lämnas helt orörda men räknas in i balansen.
    """
    teams = {
        row["id"]: row
        for row in all_rows(
            "SELECT * FROM teams WHERE tournament_id=?",
            (tournament_id,),
        )
    }
    groups = all_rows(
        "SELECT id FROM groups WHERE tournament_id=? ORDER BY name,id",
        (tournament_id,),
    )
    changed = 0

    for group in groups:
        matches = all_rows(
            """SELECT * FROM matches
               WHERE group_id=? AND stage='Gruppspel'
               ORDER BY match_no,id""",
            (group["id"],),
        )
        if not matches:
            continue

        home_counts = {}
        away_counts = {}
        editable = []

        # Spelade matcher är låsta, men deras hemma/borta-fördelning påverkar fortsatt balans.
        for match_row in matches:
            try:
                home_id = int(match_row["home_source"].split(":")[1])
                away_id = int(match_row["away_source"].split(":")[1])
            except (AttributeError, IndexError, ValueError):
                continue

            if match_row["home_score"] is not None or match_row["away_score"] is not None:
                home_counts[home_id] = home_counts.get(home_id, 0) + 1
                away_counts[away_id] = away_counts.get(away_id, 0) + 1
            else:
                editable.append((match_row, home_id, away_id))

        forced = []
        flexible = []

        # Färg bedöms i båda riktningarna. Om bara en riktning krockar är valet tvingande.
        for match_row, team_a_id, team_b_id in editable:
            team_a = teams.get(team_a_id)
            team_b = teams.get(team_b_id)
            if not team_a or not team_b:
                flexible.append((match_row, team_a_id, team_b_id))
                continue

            conflict_a_home = kit_color_conflict(team_a, team_b)
            conflict_b_home = kit_color_conflict(team_b, team_a)

            if conflict_a_home != conflict_b_home:
                if not conflict_a_home:
                    forced.append((match_row, team_a_id, team_b_id))
                else:
                    forced.append((match_row, team_b_id, team_a_id))
            else:
                # Båda riktningar är lika bra färgmässigt: använd dem för balans.
                flexible.append((match_row, team_a_id, team_b_id))

        orientations = {}

        # Tvingade färgval går först eftersom färgkrockar har högre prioritet.
        for match_row, home_id, away_id in forced:
            orientations[match_row["id"]] = [home_id, away_id, False]
            home_counts[home_id] = home_counts.get(home_id, 0) + 1
            away_counts[away_id] = away_counts.get(away_id, 0) + 1

        # Därefter balanseras matcher där båda riktningarna är färgmässigt likvärdiga.
        for match_row, team_a_id, team_b_id in flexible:
            score_ab = orientation_balance_score(
                team_a_id, team_b_id, home_counts, away_counts
            )
            score_ba = orientation_balance_score(
                team_b_id, team_a_id, home_counts, away_counts
            )

            if score_ab < score_ba:
                home_id, away_id = team_a_id, team_b_id
            elif score_ba < score_ab:
                home_id, away_id = team_b_id, team_a_id
            else:
                # Stabil tie-break: laget med färre hemmamatcher får hemma.
                a_home = home_counts.get(team_a_id, 0)
                b_home = home_counts.get(team_b_id, 0)
                if a_home < b_home:
                    home_id, away_id = team_a_id, team_b_id
                elif b_home < a_home:
                    home_id, away_id = team_b_id, team_a_id
                else:
                    # Alternera deterministiskt för att undvika ID-bias.
                    if int(match_row["match_no"] or match_row["id"]) % 2:
                        home_id, away_id = team_a_id, team_b_id
                    else:
                        home_id, away_id = team_b_id, team_a_id

            orientations[match_row["id"]] = [home_id, away_id, True]
            home_counts[home_id] = home_counts.get(home_id, 0) + 1
            away_counts[away_id] = away_counts.get(away_id, 0) + 1

        # Lokal förbättring: vänd endast flexibla matcher om den totala obalansen minskar.
        # Färgresultatet kan då inte försämras eftersom dessa matcher var färgmässigt likvärdiga.
        for _ in range(6):
            improved = False
            for match_id, orientation in orientations.items():
                home_id, away_id, is_flexible = orientation
                if not is_flexible:
                    continue

                before = (
                    abs(home_counts.get(home_id, 0) - away_counts.get(home_id, 0))
                    + abs(home_counts.get(away_id, 0) - away_counts.get(away_id, 0))
                )

                after_home_home = home_counts.get(home_id, 0) - 1
                after_home_away = away_counts.get(home_id, 0) + 1
                after_away_home = home_counts.get(away_id, 0) + 1
                after_away_away = away_counts.get(away_id, 0) - 1
                after = (
                    abs(after_home_home - after_home_away)
                    + abs(after_away_home - after_away_away)
                )

                if after < before:
                    home_counts[home_id] -= 1
                    away_counts[home_id] = away_counts.get(home_id, 0) + 1
                    home_counts[away_id] = home_counts.get(away_id, 0) + 1
                    away_counts[away_id] -= 1
                    orientation[0], orientation[1] = away_id, home_id
                    improved = True
            if not improved:
                break

        updates = []
        match_by_id = {m["id"]: m for m in matches}
        for match_id, (home_id, away_id, _is_flexible) in orientations.items():
            original = match_by_id[match_id]
            new_home = f"team:{home_id}"
            new_away = f"team:{away_id}"
            if original["home_source"] != new_home or original["away_source"] != new_away:
                updates.append((new_home, new_away, match_id))

        if updates:
            with db() as con:
                con.executemany(
                    "UPDATE matches SET home_source=?,away_source=? WHERE id=?",
                    updates,
                )
                con.commit()
            changed += len(updates)

    if changed:
        _clear_render_query_cache()
    return changed


def centered_table(dataframe):
    """Bakåtkompatibel hjälpare. Själva visningen görs av render_centered_table."""
    return dataframe


def render_centered_table(dataframe, empty_text="Ingen data att visa."):
    """Rendera en responsiv HTML-tabell med centrerade rubriker och celler."""
    if dataframe is None or dataframe.empty:
        st.info(empty_text)
        return

    display_dataframe = _translate_dataframe_for_display(dataframe)
    table_html = display_dataframe.to_html(
        index=False,
        escape=True,
        classes="cup-centered-table",
        border=0,
    )

    html_block = f"""
<style>
.cup-table-scroll {{
    width:100%;
    overflow-x:auto;
    -webkit-overflow-scrolling:touch;
    border:1px solid #cbd5e1;
    border-radius:10px;
    background:#ffffff;
}}
.cup-centered-table {{
    width:100%;
    border-collapse:collapse;
    color:#0f172a;
    background:#ffffff;
}}
.cup-centered-table th,
.cup-centered-table td {{
    text-align:center !important;
    vertical-align:middle !important;
    padding:9px 10px;
    border-bottom:1px solid #e2e8f0;
    border-right:1px solid #e2e8f0;
    white-space:nowrap;
}}
.cup-centered-table th {{
    background:#f1f5f9;
    color:#0f172a;
    font-weight:800;
}}
.cup-centered-table tr:last-child td {{
    border-bottom:none;
}}
.cup-centered-table th:last-child,
.cup-centered-table td:last-child {{
    border-right:none;
}}
</style>
<div class="cup-table-scroll">{table_html}</div>
"""
    st.markdown(html_block, unsafe_allow_html=True)


def brackets_for_display(tournament_id):
    """Visa högst ett A- och ett B-slutspel även om äldre data innehåller dubbletter."""
    rows = all_rows("SELECT * FROM brackets WHERE tournament_id=? ORDER BY id", (tournament_id,))
    regular = []
    selected = {}
    duplicates = []
    for bracket in rows:
        key = bracket["name"].strip().casefold()
        if key not in {"a-slutspel", "b-slutspel"}:
            regular.append(bracket)
            continue
        completed = one_row(
            "SELECT COUNT(*) AS n FROM matches WHERE bracket_id=? AND home_score IS NOT NULL AND away_score IS NOT NULL",
            (bracket["id"],),
        )["n"]
        total = one_row("SELECT COUNT(*) AS n FROM matches WHERE bracket_id=?", (bracket["id"],))["n"]
        candidate = (completed, total, bracket["id"], bracket)
        if key not in selected or candidate[:3] > selected[key][:3]:
            if key in selected:
                duplicates.append(selected[key][3])
            selected[key] = candidate
        else:
            duplicates.append(bracket)
    visible = regular + [value[3] for value in selected.values()]
    return sorted(visible, key=lambda bracket: bracket["id"]), duplicates


def create_round_robin(tournament_id, group_id):
    team_ids = [r["id"] for r in all_rows("SELECT id FROM teams WHERE group_id=? ORDER BY id", (group_id,))]
    if len(team_ids) < 2:
        return 0
    existing = {
        tuple(sorted((int(m["home_source"].split(":")[1]), int(m["away_source"].split(":")[1]))))
        for m in all_rows("SELECT home_source, away_source FROM matches WHERE group_id=? AND stage='Gruppspel'", (group_id,))
    }
    created = 0
    match_no = len(existing) + 1
    for i, home in enumerate(team_ids):
        for away in team_ids[i + 1:]:
            if tuple(sorted((home, away))) in existing:
                continue
            run(
                "INSERT INTO matches(tournament_id,group_id,stage,match_no,home_source,away_source) VALUES(?,?,'Gruppspel',?,?,?)",
                (tournament_id, group_id, match_no, f"team:{home}", f"team:{away}"),
            )
            created += 1; match_no += 1
    optimize_group_home_away(tournament_id)
    return created


def create_all_group_matches(tournament_id):
    """Skapa alla saknade enkelmöten via schemadomänens repository."""
    repo = schedule_repository()
    groups, all_team_rows, all_existing_rows = repo.group_generation_data(tournament_id)

    teams_by_group = {}
    for row in all_team_rows:
        teams_by_group.setdefault(row["group_id"], []).append(row["id"])

    existing_by_group = {}
    for match_row in all_existing_rows:
        try:
            pair = tuple(sorted((
                int(match_row["home_source"].split(":")[1]),
                int(match_row["away_source"].split(":")[1]),
            )))
        except (ValueError, IndexError, AttributeError):
            continue
        existing_by_group.setdefault(match_row["group_id"], set()).add(pair)

    created = 0
    ready_groups = 0
    skipped_groups = []
    pending = []
    for group in groups:
        team_ids = teams_by_group.get(group["id"], [])
        if len(team_ids) < 2:
            skipped_groups.append(group["name"])
            continue
        ready_groups += 1
        existing = existing_by_group.get(group["id"], set())
        match_no = len(existing) + 1
        for i, home in enumerate(team_ids):
            for away in team_ids[i + 1:]:
                pair = tuple(sorted((home, away)))
                if pair in existing:
                    continue
                pending.append((tournament_id, group["id"], match_no, f"team:{home}", f"team:{away}"))
                existing.add(pair)
                created += 1
                match_no += 1

    if pending:
        repo.insert_group_matches(pending)

    # Optimera även befintliga ospelade gruppmatcher så att regenerering förbättrar
    # färgval och hemma/borta-fördelning, utan att röra spelade matcher.
    optimize_group_home_away(tournament_id)
    return created, ready_groups, skipped_groups


def create_bracket(tournament_id, name, size, bronze, first_sources):
    bracket_id = run("INSERT INTO brackets(tournament_id,name,size,bronze_match) VALUES(?,?,?,?)", (tournament_id, name, size, int(bronze)))
    first_stage = {2: "Final", 4: "Semifinal", 8: "Kvartsfinal"}[size]
    previous_ids = []
    for i in range(size // 2):
        mid = run(
            "INSERT INTO matches(tournament_id,bracket_id,stage,round_no,match_no,home_source,away_source) VALUES(?,?,?,?,?,?,?)",
            (tournament_id, bracket_id, first_stage, 1, i + 1, first_sources[i * 2], first_sources[i * 2 + 1]),
        )
        previous_ids.append(mid)
    semifinal_ids = previous_ids if size == 4 else []
    round_no = 2
    while len(previous_ids) > 1:
        next_ids = []
        stage = "Final" if len(previous_ids) == 2 else "Semifinal"
        for i in range(0, len(previous_ids), 2):
            mid = run(
                "INSERT INTO matches(tournament_id,bracket_id,stage,round_no,match_no,home_source,away_source) VALUES(?,?,?,?,?,?,?)",
                (tournament_id, bracket_id, stage, round_no, i // 2 + 1, f"winner:{previous_ids[i]}", f"winner:{previous_ids[i+1]}"),
            )
            next_ids.append(mid)
        if stage == "Semifinal":
            semifinal_ids = next_ids
        previous_ids = next_ids; round_no += 1
    if bronze and len(semifinal_ids) == 2:
        run(
            "INSERT INTO matches(tournament_id,bracket_id,stage,round_no,match_no,home_source,away_source) VALUES(?,?,?,?,?,?,?)",
            (tournament_id, bracket_id, "Bronsmatch", round_no, 1, f"loser:{semifinal_ids[0]}", f"loser:{semifinal_ids[1]}"),
        )


PLACEMENT_PLAYOFF_FORMAT = "Placeringsslutspel – ettor mot ettor osv."


def placement_playoff_specs(tournament_id):
    """Bygg dynamiska placeringsslutspel för två, fyra eller åtta grupper."""
    groups = all_rows("SELECT * FROM groups WHERE tournament_id=? ORDER BY name", (tournament_id,))
    team_counts = {
        group["id"]: one_row("SELECT COUNT(*) AS n FROM teams WHERE group_id=?", (group["id"],))["n"]
        for group in groups
    }
    if len(groups) not in {2, 4, 8} or any(team_counts[group["id"]] < 2 for group in groups):
        return [], "Placeringsslutspel kräver två, fyra eller åtta grupper med minst två lag i varje grupp."
    max_rank = min(team_counts.values())
    rank_names = {1: "Ettornas slutspel", 2: "Tvåornas slutspel", 3: "Treornas slutspel", 4: "Fyrornas slutspel"}
    specs = []
    for rank in range(1, max_rank + 1):
        name = rank_names.get(rank, f"Placering {rank}-slutspel")
        specs.append((name, len(groups), [f"group:{group['id']}:{rank}" for group in groups]))
    return specs, ""


def sync_placement_playoffs(tournament_id, bronze_match):
    """Skapa platshållarmatcher automatiskt och behåll redan spelade slutspel orörda."""
    tournament = one_row("SELECT playoff_format FROM tournaments WHERE id=?", (tournament_id,))
    if not tournament or tournament["playoff_format"] != PLACEMENT_PLAYOFF_FORMAT:
        return False
    specs, error = placement_playoff_specs(tournament_id)
    if error:
        return False
    existing = all_rows("SELECT * FROM brackets WHERE tournament_id=? ORDER BY id", (tournament_id,))
    existing_signature = []
    for bracket in existing:
        first_round = all_rows(
            "SELECT home_source,away_source FROM matches WHERE bracket_id=? AND round_no=1 ORDER BY match_no",
            (bracket["id"],),
        )
        sources = [source for match_row in first_round for source in (match_row["home_source"], match_row["away_source"])]
        existing_signature.append((bracket["name"], bracket["size"], sources))
    desired_signature = [(name, size, sources) for name, size, sources in specs]
    if existing_signature == desired_signature:
        return False
    played = one_row(
        "SELECT COUNT(*) AS n FROM matches WHERE tournament_id=? AND bracket_id IS NOT NULL AND home_score IS NOT NULL",
        (tournament_id,),
    )["n"]
    if played:
        return False
    run("DELETE FROM brackets WHERE tournament_id=?", (tournament_id,))
    for bracket_name, bracket_size, bracket_sources in specs:
        create_bracket(tournament_id, bracket_name, bracket_size, bool(bronze_match) and bracket_size >= 4, bracket_sources)
    return True


def playoff_specs_for_tournament(tournament_id, tournament):
    """Returnera önskat slutspel utifrån den modell som valts på Adminöversikten."""
    fmt = tournament["playoff_format"]
    if fmt == "Inget slutspel":
        return [], ""
    if fmt == "A- och B-slutspel":
        groups = all_rows("SELECT * FROM groups WHERE tournament_id=? ORDER BY name", (tournament_id,))
        if len(groups) != 2:
            return [], "A- och B-slutspel kräver exakt två grupper."
        counts = {
            group["id"]: one_row("SELECT COUNT(*) AS n FROM teams WHERE group_id=?", (group["id"],))["n"]
            for group in groups
        }
        if any(counts[group["id"]] < 4 for group in groups):
            return [], "A- och B-slutspel kräver minst fyra lag i vardera gruppen."
        group_a, group_b = groups
        return [
            ("A-slutspel", 4, [
                f"group:{group_a['id']}:1", f"group:{group_b['id']}:2",
                f"group:{group_b['id']}:1", f"group:{group_a['id']}:2",
            ]),
            ("B-slutspel", 4, [
                f"group:{group_a['id']}:3", f"group:{group_b['id']}:4",
                f"group:{group_b['id']}:3", f"group:{group_a['id']}:4",
            ]),
        ], ""
    if fmt == PLACEMENT_PLAYOFF_FORMAT:
        return placement_playoff_specs(tournament_id)
    return [], "Okänd slutspelsmodell."


def ensure_playoffs_for_schedule(tournament_id, tournament):
    """Skapa/uppdatera slutspel automatiskt när hela schemat genereras."""
    specs, error = playoff_specs_for_tournament(tournament_id, tournament)
    if error:
        return False, error

    existing = all_rows("SELECT * FROM brackets WHERE tournament_id=? ORDER BY id", (tournament_id,))
    existing_signature = []
    for bracket in existing:
        first_round = all_rows(
            "SELECT home_source,away_source FROM matches WHERE bracket_id=? AND round_no=1 ORDER BY match_no",
            (bracket["id"],),
        )
        sources = [source for row in first_round for source in (row["home_source"], row["away_source"])]
        existing_signature.append((bracket["name"], int(bracket["size"]), sources))
    desired_signature = [(name, int(size), sources) for name, size, sources in specs]

    if existing_signature == desired_signature:
        return True, ""

    played = one_row(
        "SELECT COUNT(*) AS n FROM matches WHERE tournament_id=? AND bracket_id IS NOT NULL AND home_score IS NOT NULL",
        (tournament_id,),
    )["n"]
    if played:
        return False, "Slutspelsmodellen kan inte byggas om eftersom slutspelsresultat redan är registrerade."

    run("DELETE FROM brackets WHERE tournament_id=?", (tournament_id,))
    for bracket_name, bracket_size, bracket_sources in specs:
        create_bracket(
            tournament_id,
            bracket_name,
            bracket_size,
            bool(tournament["bronze_match"]) and bracket_size >= 4,
            bracket_sources,
        )
    return True, ""


def render_group_table(table_rows, tournament):
    """Text-TV-inspirerad grupptabell med tydlig markering av A/B-slutspelsplatser."""
    if not table_rows:
        st.info("Ingen tabelldata att visa.")
        return
    rows_html = []
    fmt = tournament["playoff_format"]
    for position, (_, data) in enumerate(table_rows, 1):
        qualifier = ""
        row_class = ""
        if fmt == "A- och B-slutspel":
            if position <= 2:
                qualifier = "<span class='qualifier a'>A</span>"
                row_class = "qual-a"
            elif position <= 4:
                qualifier = "<span class='qualifier b'>B</span>"
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
        .texttv-wrap{{overflow-x:auto;border:2px solid #172554;border-radius:8px;background:#07111f;padding:6px}}
        .texttv-table{{width:100%;border-collapse:collapse;font-family:ui-monospace,SFMono-Regular,Consolas,monospace;color:#f8fafc}}
        .texttv-table th,.texttv-table td{{text-align:center!important;padding:8px 9px;border-bottom:1px solid #334155}}
        .texttv-table th{{background:#172554;color:#facc15;font-weight:900}}
        .texttv-table td.team{{text-align:left!important;font-weight:800}}
        .texttv-table tr.qual-a{{background:rgba(22,163,74,.20)}}
        .texttv-table tr.qual-b{{background:rgba(37,99,235,.20)}}
        .qualifier{{display:inline-flex;width:24px;height:24px;align-items:center;justify-content:center;border-radius:4px;color:#fff;font-weight:900}}
        .qualifier.a,.texttv-legend i.a{{background:#16a34a}}
        .qualifier.b,.texttv-legend i.b{{background:#2563eb}}
        .texttv-legend{{display:flex;gap:18px;margin-top:7px;color:#334155;font-size:13px}}
        .texttv-legend span{{display:flex;align-items:center;gap:6px}}
        .texttv-legend i{{width:13px;height:13px;border-radius:2px;display:inline-block}}
        </style>
        <div class="texttv-wrap"><table class="texttv-table">
        <thead><tr><th>Pl</th><th>Lag</th><th>S</th><th>V</th><th>O</th><th>F</th><th>GM</th><th>IM</th><th>MS</th><th>P</th><th>Slutspel</th></tr></thead>
        <tbody>{''.join(rows_html)}</tbody></table></div>{legend}
        """,
        unsafe_allow_html=True,
    )



def generate_schedule(tournament_id, tournament, rules, preserve_existing=False):
    repo = schedule_repository()

    def schedule_source_id(source):
        direct_team_id = schedule_source_team_id(source)
        if direct_team_id is not None:
            return direct_team_id
        return resolve_source(source)

    try:
        schedule_window = build_schedule_window(tournament, rules)
    except (TypeError, ValueError, KeyError):
        return 0, 0, "Turneringen måste ha giltiga cupdatum, första avspark och sista plantid."

    start = schedule_window.start
    end_date = schedule_window.end_date
    latest_kickoff = schedule_window.latest_pitch_time
    duration = schedule_window.group_match_duration

    def duration_for_match(match_row):
        return schedule_window.duration_for_stage(match_row["stage"])

    def valid_daily_start_for(candidate, match_duration):
        candidate_end = candidate + match_duration
        day_limit = datetime.combine(candidate.date(), latest_kickoff)
        if candidate_end > day_limit:
            candidate = datetime.combine(candidate.date() + timedelta(days=1), start.time())
            candidate_end = candidate + match_duration
            day_limit = datetime.combine(candidate.date(), latest_kickoff)
        if candidate.date() > end_date or candidate_end > day_limit:
            return None
        return candidate

    def valid_daily_start(candidate):
        # latest_kickoff_time behålls som databasnamn för kompatibilitet, men värdet betyder sista plantid.
        # Matchen måste vara färdig innan planerna stänger.
        candidate_end = candidate + duration
        day_limit = datetime.combine(candidate.date(), latest_kickoff)
        if candidate_end > day_limit:
            candidate = datetime.combine(candidate.date() + timedelta(days=1), start.time())
            candidate_end = candidate + duration
            day_limit = datetime.combine(candidate.date(), latest_kickoff)
        if candidate.date() > end_date or candidate_end > day_limit:
            return None
        return candidate
    # Databasen ändras först när hela schemaläggningspasset är färdigberäknat.
    # Det minskar risken för ett halvuppdaterat schema om ett oväntat fel inträffar.
    schedule_updates = []
    pitch_gap = timedelta(minutes=rules["pitch_break_minutes"])
    avoid_consecutive = bool(rules["avoid_consecutive_matches"])
    consecutive_break = timedelta(minutes=rules["consecutive_match_break_minutes"] if avoid_consecutive else 0)
    pitch_ready = {pitch: start for pitch in range(1, rules["pitch_count"] + 1)}
    team_ready = {}
    team_last_end = {}
    referees, travel_preference_rows, matches = repo.scheduling_inputs(tournament_id)
    referee_ready = {r["id"]: start for r in referees}
    travel_preferences = {
        row["id"]: row
        for row in travel_preference_rows
    }

    def apply_first_match_preference(candidate, team_id):
        preference = travel_preferences.get(team_id)
        if not preference or not preference["late_first_match"] or not preference["earliest_first_time"]:
            return candidate
        # Önskemålet gäller bara lagets första match i turneringen.
        if team_id in team_last_end:
            return candidate
        try:
            preferred_time = datetime.strptime(preference["earliest_first_time"], "%H:%M").time()
        except (TypeError, ValueError):
            return candidate
        preferred_start = datetime.combine(start.date(), preferred_time)
        return max(candidate, preferred_start)

    locked_events = []
    if preserve_existing:
        for existing_match in matches:
            if not existing_match["scheduled_start"] or not existing_match["pitch_number"]:
                continue
            home_id = schedule_source_id(existing_match["home_source"])
            away_id = schedule_source_id(existing_match["away_source"])
            if not home_id or not away_id:
                continue
            existing_start = datetime.fromisoformat(existing_match["scheduled_start"])
            existing_end = existing_start + duration_for_match(existing_match)
            pitch = existing_match["pitch_number"]
            pitch_ready[pitch] = max(pitch_ready.get(pitch, start), existing_end + pitch_gap)
            team_ready[home_id] = max(team_ready.get(home_id, start), existing_end + consecutive_break)
            team_ready[away_id] = max(team_ready.get(away_id, start), existing_end + consecutive_break)
            team_last_end[home_id] = max(team_last_end.get(home_id, start), existing_end)
            team_last_end[away_id] = max(team_last_end.get(away_id, start), existing_end)
            if existing_match["referee_id"] in referee_ready:
                referee_ready[existing_match["referee_id"]] = max(referee_ready[existing_match["referee_id"]], existing_end + pitch_gap)
    else:
        for locked_match in matches:
            if not locked_match["schedule_locked"] or not locked_match["scheduled_start"] or not locked_match["pitch_number"]:
                continue
            locked_home = schedule_source_id(locked_match["home_source"])
            locked_away = schedule_source_id(locked_match["away_source"])
            locked_start = datetime.fromisoformat(locked_match["scheduled_start"])
            locked_events.append({
                "start": locked_start, "end": locked_start + duration_for_match(locked_match), "pitch": locked_match["pitch_number"],
                "referee": locked_match["referee_id"], "teams": {locked_home, locked_away} - {None},
            })

    def move_past_locked(candidate_start, pitch, referee_id, home_id, away_id, match_duration):
        candidate_teams = {home_id, away_id}
        changed = True
        while changed:
            changed = False
            candidate_end = candidate_start + match_duration
            for locked in locked_events:
                blocked_until = None
                if pitch == locked["pitch"] and candidate_start < locked["end"] + pitch_gap and candidate_end + pitch_gap > locked["start"]:
                    blocked_until = locked["end"] + pitch_gap
                if referee_id and referee_id == locked["referee"] and candidate_start < locked["end"] and candidate_end > locked["start"]:
                    blocked_until = max(blocked_until or locked["end"], locked["end"])
                if candidate_teams & locked["teams"] and candidate_start < locked["end"] + consecutive_break and candidate_end + consecutive_break > locked["start"]:
                    blocked_until = max(blocked_until or locked["end"] + consecutive_break, locked["end"] + consecutive_break)
                if blocked_until and blocked_until > candidate_start:
                    candidate_start = blocked_until
                    changed = True
                    break
        return valid_daily_start(candidate_start)
    scheduled = 0
    unresolved = 0
    remaining = []
    placeholder_matches = []
    for match_row in matches:
        if match_row["scheduled_start"] and (preserve_existing or match_row["schedule_locked"]):
            continue
        home_id = schedule_source_id(match_row["home_source"])
        away_id = schedule_source_id(match_row["away_source"])
        if not home_id or not away_id:
            # Slutspelsmatcher ska ändå få tid, plan och matchnummer redan innan lagen är klara.
            placeholder_matches.append(match_row)
            continue
        remaining.append((match_row, home_id, away_id))
    # Optimera ordningen på konkreta matcher före exakt placering. OR-Tools
    # löser parallella schemavågor när biblioteket finns tillgängligt; den
    # befintliga schemaläggaren ansvarar fortfarande för exakta tider, låsta
    # matcher, domare, reseönskemål och slutspelsberoenden.
    if remaining:
        optimized_order, optimization_engine = optimize_match_order(
            remaining,
            pitch_count=int(rules.get("pitch_count") or 1),
            time_limit_seconds=2.0,
        )
        remaining = [remaining[index] for index in optimized_order]
    else:
        optimization_engine = "trivial"

    last_scheduled_teams = set()
    forced_consecutive = 0
    while remaining:
        candidates = []
        for order, (match_row, home_id, away_id) in enumerate(remaining):
            for pitch in pitch_ready:
                consecutive_penalty = int(avoid_consecutive and bool({home_id, away_id} & last_scheduled_teams))
                basic_start = max(pitch_ready[pitch], team_ready.get(home_id, start), team_ready.get(away_id, start))
                basic_start = apply_first_match_preference(basic_start, home_id)
                basic_start = apply_first_match_preference(basic_start, away_id)
                if consecutive_penalty:
                    basic_start = max(
                        basic_start,
                        team_last_end.get(home_id, start) + consecutive_break,
                        team_last_end.get(away_id, start) + consecutive_break,
                    )
                match_duration = duration_for_match(match_row)
                if rules["referee_mode"] == "Automatisk" and referees:
                    for referee in referees:
                        referee_id = referee["id"]
                        candidate_start = valid_daily_start_for(max(basic_start, referee_ready[referee_id]), match_duration)
                        candidate_start = move_past_locked(candidate_start, pitch, referee_id, home_id, away_id, match_duration) if candidate_start else None
                        if candidate_start:
                            candidates.append((candidate_start, consecutive_penalty, order, pitch, referee_id))
                else:
                    candidate_start = valid_daily_start_for(basic_start, match_duration)
                    candidate_start = move_past_locked(candidate_start, pitch, match_row["referee_id"], home_id, away_id, match_duration) if candidate_start else None
                    if candidate_start:
                        candidates.append((candidate_start, consecutive_penalty, order, pitch, match_row["referee_id"]))
        if not candidates:
            unresolved += len(remaining)
            days = (end_date - start.date()).days + 1
            daily_minutes = int((datetime.combine(start.date(), latest_kickoff) - start).total_seconds() // 60)
            slot_minutes = max(1, int(duration.total_seconds() // 60) + rules["pitch_break_minutes"])
            if daily_minutes >= int(duration.total_seconds() // 60):
                starts_per_pitch_day = 1 + max(0, (daily_minutes - int(duration.total_seconds() // 60)) // slot_minutes)
            else:
                starts_per_pitch_day = 0
            theoretical_capacity = starts_per_pitch_day * rules["pitch_count"] * max(days, 0)
            reasons = []
            if len(matches) > theoretical_capacity:
                reasons.append(
                    f"det finns teoretiskt högst {theoretical_capacity} planplatser för {len(matches)} matcher med nuvarande tider"
                )
            if rules["referee_mode"] == "Automatisk" and not referees:
                reasons.append("inga domare är registrerade för automatisk tillsättning")
            late_requests = sum(1 for pref in travel_preferences.values() if pref["late_first_match"] and pref["earliest_first_time"])
            if late_requests:
                reasons.append(f"{late_requests} lag har önskemål om senare första match")
            if avoid_consecutive:
                reasons.append(f"kravet på extra lagvila är {rules['consecutive_match_break_minutes']} minuter")
            reason_text = "; ".join(reasons) if reasons else "kombinationen av plan-, lag-, domar- och tidsbegränsningar"
            warning = (
                "Alla matcher fick inte plats inom cupens datumintervall och sista plantid. "
                f"Möjliga orsaker: {reason_text}."
            )
            break
        sort_key = (
            (lambda item: (item[1], item[0], item[2], item[3], item[4] or 0))
            if avoid_consecutive else
            (lambda item: (item[0], item[2], item[3], item[4] or 0))
        )
        match_start, consecutive_penalty, order, pitch, referee_id = min(candidates, key=sort_key)
        match_row, home_id, away_id = remaining.pop(order)
        forced_consecutive += consecutive_penalty
        last_scheduled_teams = {home_id, away_id}
        match_end = match_start + duration_for_match(match_row)
        schedule_updates.append(
            (match_start.isoformat(timespec="minutes"), pitch, referee_id, match_row["id"])
        )
        pitch_ready[pitch] = match_end + pitch_gap
        team_ready[home_id] = match_end + consecutive_break
        team_ready[away_id] = match_end + consecutive_break
        team_last_end[home_id] = match_end
        team_last_end[away_id] = match_end
        if referee_id and rules["referee_mode"] == "Automatisk":
            referee_ready[referee_id] = match_end + pitch_gap
        scheduled += 1

    # Schemalägg därefter slutspelsplatshållare. De får riktiga tider och löpnummer
    # även om gruppvinnare/semifinalvinnare ännu inte är kända.
    scheduled_start_by_id = {}
    scheduled_end_by_id = {}
    for existing_match in matches:
        if existing_match["scheduled_start"]:
            existing_start = datetime.fromisoformat(existing_match["scheduled_start"])
            existing_duration = duration_for_match(existing_match)
            scheduled_start_by_id[existing_match["id"]] = existing_start
            scheduled_end_by_id[existing_match["id"]] = existing_start + existing_duration
    match_by_id = {m["id"]: m for m in matches}
    for start_iso, _, _, match_id in schedule_updates:
        scheduled_start = datetime.fromisoformat(start_iso)
        scheduled_start_by_id[match_id] = scheduled_start
        scheduled_end_by_id[match_id] = scheduled_start + duration_for_match(match_by_id[match_id])

    group_match_ids = {}
    for m in matches:
        if m["stage"] == "Gruppspel" and m["group_id"]:
            group_match_ids.setdefault(m["group_id"], []).append(m["id"])

    def source_dependency_ready(source):
        parts = source.split(":") if source else []
        if not parts:
            return start
        if parts[0] == "group":
            group_id = int(parts[1])
            ids = group_match_ids.get(group_id, [])
            if not ids or any(match_id not in scheduled_end_by_id for match_id in ids):
                return None
            return max(scheduled_end_by_id[match_id] for match_id in ids) + consecutive_break
        if parts[0] in ("winner", "loser"):
            feeder_id = int(parts[1])
            if feeder_id not in scheduled_end_by_id:
                return None
            return scheduled_end_by_id[feeder_id] + consecutive_break
        return start

    pending_placeholders = list(placeholder_matches)
    while pending_placeholders:
        progress = False
        for match_row in list(pending_placeholders):
            home_ready = source_dependency_ready(match_row["home_source"])
            away_ready = source_dependency_ready(match_row["away_source"])
            if home_ready is None or away_ready is None:
                continue
            match_duration = duration_for_match(match_row)
            basic_start = max(home_ready, away_ready, start)
            candidates = []
            for pitch in pitch_ready:
                base = max(basic_start, pitch_ready[pitch])
                if rules["referee_mode"] == "Automatisk" and referees:
                    for referee in referees:
                        referee_id = referee["id"]
                        candidate = valid_daily_start_for(max(base, referee_ready[referee_id]), match_duration)
                        if candidate:
                            candidates.append((candidate, pitch, referee_id))
                else:
                    candidate = valid_daily_start_for(base, match_duration)
                    if candidate:
                        candidates.append((candidate, pitch, match_row["referee_id"]))
            if not candidates:
                continue
            match_start, pitch, referee_id = min(candidates, key=lambda item: (item[0], item[1], item[2] or 0))
            match_end = match_start + match_duration
            schedule_updates.append((match_start.isoformat(timespec="minutes"), pitch, referee_id, match_row["id"]))
            scheduled_start_by_id[match_row["id"]] = match_start
            scheduled_end_by_id[match_row["id"]] = match_end
            pitch_ready[pitch] = match_end + pitch_gap
            if referee_id and rules["referee_mode"] == "Automatisk":
                referee_ready[referee_id] = match_end + pitch_gap
            scheduled += 1
            pending_placeholders.remove(match_row)
            progress = True
        if not progress:
            unresolved += len(pending_placeholders)
            warning = (
                (locals().get("warning", "") + " ").strip()
                + f"{len(pending_placeholders)} slutspelsmatch(er) kunde inte få en tid inom cupens plantider."
            ).strip()
            break

    warning = locals().get("warning", "")
    if rules["referee_mode"] == "Automatisk" and not referees:
        referee_warning = "Schemat skapades utan domare eftersom inga domare är registrerade."
        warning = f"{warning} {referee_warning}".strip()
    if forced_consecutive:
        consecutive_warning = (
            f"Schemat behövde placera {forced_consecutive} match(er) efter en match med samma lag; "
            f"den angivna extrapusen på {rules['consecutive_match_break_minutes']} minuter lades in."
        )
        warning = f"{warning} {consecutive_warning}".strip()

    if optimization_engine == "greedy-fallback":
        warning = f"{warning} OR-Tools var inte tillgängligt; säker standardoptimering användes.".strip()

    # Spara hela schemaläggningspasset atomiskt via repository-lagret.
    try:
        repo.persist_generated_schedule(
            tournament_id=tournament_id,
            schedule_updates=schedule_updates,
            unresolved=unresolved,
            preserve_existing=preserve_existing,
        )
    except Exception as exc:
        return 0, len(schedule_updates) + unresolved, f"Schemat kunde inte sparas och inga schemaändringar genomfördes: {exc}"

    return scheduled, unresolved, warning


def validate_schedule(tournament_id, tournament, rules):
    """Kontrollera schemat och sammanställ väntetid och belastning per lag."""
    rows = schedule_repository().scheduled_matches(tournament_id)
    duration = timedelta(minutes=(rules["halves"] * rules["minutes_per_half"]) + ((rules["halves"] - 1) * rules["halftime_minutes"]))
    playoff_extra = timedelta(
        minutes=int(tournament["extra_time_minutes"] or 0)
        if tournament["playoff_tie_rule"] == "Förlängning + straffar" else 0
    )
    pitch_gap = timedelta(minutes=rules["pitch_break_minutes"])
    avoid_consecutive = bool(rules["avoid_consecutive_matches"])
    consecutive_break_minutes = rules["consecutive_match_break_minutes"] if avoid_consecutive else 0
    cup_start = datetime.fromisoformat(tournament["start_date"] or tournament["tournament_date"]).date()
    cup_end = datetime.fromisoformat(tournament["end_date"] or tournament["start_date"] or tournament["tournament_date"]).date()
    first_time = datetime.strptime(rules["first_match_time"], "%H:%M").time()
    latest_time = datetime.strptime(rules["latest_kickoff_time"], "%H:%M").time()
    errors, warnings = [], []
    events = []
    for number, match_row in enumerate(rows, 1):
        start_at = datetime.fromisoformat(match_row["scheduled_start"])
        match_duration = duration + (playoff_extra if match_row["stage"] != "Gruppspel" else timedelta(0))
        home_id, away_id = resolve_source(match_row["home_source"]), resolve_source(match_row["away_source"])
        home_team, away_team = team(home_id), team(away_id)
        events.append({"number": number, "row": match_row, "start": start_at, "end": start_at + match_duration, "teams": {home_id, away_id} - {None}})
        if not cup_start <= start_at.date() <= cup_end:
            errors.append(f"Match {number} ligger utanför cupens datumintervall.")
        if start_at.time() < first_time:
            errors.append(f"Match {number} har avspark {start_at.strftime('%H:%M')} före första tillåtna avspark.")
        if (start_at + match_duration) > datetime.combine(start_at.date(), latest_time):
            errors.append(
                f"Match {number} slutar {(start_at + match_duration).strftime('%H:%M')}, efter sista plantid {latest_time.strftime('%H:%M')}."
            )
        if not match_row["pitch_number"] or not 1 <= match_row["pitch_number"] <= rules["pitch_count"]:
            errors.append(f"Match {number} har en ogiltig plan.")
        if rules["referee_mode"] == "Automatisk" and not match_row["referee_id"]:
            warnings.append(f"Match {number} saknar domare.")
        if kit_color_conflict(home_team, away_team):
            warnings.append(
                f"Möjlig färglikhet i match {number}: {away_team['name']}s ordinarie ställ och bortaställ ligger nära hemmalagets färger. "
                f"Ett ytterligare avvikande ställ behöver användas."
            )
    for index, first in enumerate(events):
        for second in events[index + 1:]:
            if second["start"] >= first["end"] + pitch_gap and second["start"] >= first["end"]:
                break
            if first["row"]["pitch_number"] == second["row"]["pitch_number"] and second["start"] < first["end"] + pitch_gap:
                errors.append(f"Plankrock mellan match {first['number']} och {second['number']}.")
            if first["row"]["referee_id"] and first["row"]["referee_id"] == second["row"]["referee_id"] and second["start"] < first["end"]:
                errors.append(f"Domarkrock mellan match {first['number']} och {second['number']}.")
            if first["teams"] & second["teams"] and second["start"] < first["end"]:
                errors.append(f"Ett lag är dubbelbokat i match {first['number']} och {second['number']}.")
    team_events = {}
    for event in events:
        for team_id in event["teams"]:
            team_events.setdefault(team_id, []).append(event)
    day_starts = {}
    for event in events:
        day_starts.setdefault(event["start"].date(), []).append(event["start"])
    quality_rows = []
    for team_id, team_matches in team_events.items():
        team_matches.sort(key=lambda event: event["start"])
        waits = []
        consecutive = 0
        for previous, current in zip(team_matches, team_matches[1:]):
            rest_minutes = int((current["start"] - previous["end"]).total_seconds() // 60)
            waits.append(rest_minutes)
            if avoid_consecutive and rest_minutes < consecutive_break_minutes:
                errors.append(
                    f"{team(team_id)['name']} saknar den obligatoriska extrapusen på {consecutive_break_minutes} minuter "
                    f"mellan match {previous['number']} och {current['number']}."
                )
            if rest_minutes <= rules["pitch_break_minutes"]:
                consecutive += 1
                if avoid_consecutive:
                    warnings.append(f"{team(team_id)['name']} spelar match {previous['number']} och {current['number']} direkt efter varandra.")
        team_row = team(team_id)
        if team_row and team_row["late_first_match"] and team_row["earliest_first_time"] and team_matches:
            try:
                preferred_time = datetime.strptime(team_row["earliest_first_time"], "%H:%M").time()
                first_event = team_matches[0]
                if first_event["start"].date() == cup_start and first_event["start"].time() < preferred_time:
                    warnings.append(
                        f"{team_row['name']} önskar sin första match tidigast {preferred_time.strftime('%H:%M')}, "
                        f"men är schemalagt {first_event['start'].strftime('%H:%M')}."
                    )
            except (TypeError, ValueError):
                pass
        early = sum(1 for event in team_matches if event["start"] == min(day_starts[event["start"].date()]))
        late = sum(1 for event in team_matches if event["start"] == max(day_starts[event["start"].date()]))
        quality_rows.append({
            "Lag": team(team_id)["name"], "Matcher": len(team_matches),
            "Kortaste vila": min(waits) if waits else None,
            "Genomsnittlig vila": round(sum(waits) / len(waits)) if waits else None,
            "Direkt efter": consecutive, "Tidiga matcher": early, "Sena matcher": late,
        })
    unscheduled_groups = one_row(
        "SELECT COUNT(*) AS n FROM matches WHERE tournament_id=? AND stage='Gruppspel' AND scheduled_start IS NULL",
        (tournament_id,),
    )["n"]
    if unscheduled_groups:
        errors.append(f"{unscheduled_groups} gruppspelsmatcher saknar schematid.")
    return list(dict.fromkeys(errors)), list(dict.fromkeys(warnings)), quality_rows


def render_bracket_tree(bracket_id, public=False):
    bracket_matches = all_rows("SELECT * FROM matches WHERE bracket_id=? ORDER BY round_no,match_no", (bracket_id,))
    main_stages = []
    for stage_name in ["Kvartsfinal", "Semifinal", "Final"]:
        stage_matches = [m for m in bracket_matches if m["stage"] == stage_name]
        if stage_matches:
            main_stages.append((stage_name, stage_matches))
    if not main_stages:
        st.info("Slutspelsträdet saknar matcher.")
        return

    card_width = 250
    card_height = 108
    column_gap = 92
    column_width = card_width + column_gap
    header_height = 48
    first_count = len(main_stages[0][1])
    play_height = max(330, first_count * 154)
    canvas_width = len(main_stages) * column_width - column_gap + 40
    canvas_height = header_height + play_height + 20

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
        home = team(home_id)
        away = team(away_id)
        home_name = html.escape(source_label(match_row["home_source"]))
        away_name = html.escape(source_label(match_row["away_source"]))
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

    bronze_matches = [m for m in bracket_matches if m["stage"] == "Bronsmatch"]
    bronze_html = ""
    if bronze_matches:
        bronze = bronze_matches[0]
        bronze_home = "–" if bronze["home_score"] is None else bronze["home_score"]
        bronze_away = "–" if bronze["away_score"] is None else bronze["away_score"]
        bronze_html = f"""
          <div class='classic-bronze'>
            <div><strong>🥉 Bronsmatch</strong><small>Placeringsmatch</small></div>
            <span>{html.escape(source_label(bronze['home_source']))}</span><b>{bronze_home}</b>
            <span>{html.escape(source_label(bronze['away_source']))}</span><b>{bronze_away}</b>
          </div>
        """
    st.markdown(
        f"""
        <style>
          .classic-bracket-scroll {{overflow-x:auto;padding:6px 3px 18px}}
          .classic-bracket {{position:relative;min-width:{canvas_width}px;height:{canvas_height}px;background:linear-gradient(180deg,#f8fafc 0,#fff 100%);border:1px solid #e2e8f0;border-radius:14px}}
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
          .classic-bronze b {{text-align:center}}
        </style>
        <div class="classic-bracket-scroll">
          <div class="classic-bracket">{''.join(connectors)}{''.join(headers)}{''.join(cards)}</div>
          {bronze_html}
        </div>
        """,
        unsafe_allow_html=True,
    )



def public_match_events_html(match_id, match_row=None, rows=None, team_names=None):
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
        team_id = row["team_id"]
        team_data.setdefault(team_id, {"name": row["team_name"], "events": []})
        goals = int(row["goals"] or 0)
        reds = int(row["red_cards"] or 0)
        public_player_name = "Skyddad spelare" if bool(_row_value(row, "is_protected", 0)) else row["player_name"]
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
            name = data["name"]
            events = "".join(data["events"])
        else:
            name = (team_names or {}).get(team_id, "")
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




def public_rules_html(tournament, rules):
    """Bygg lättlästa publika regler utifrån cupens sparade inställningar."""
    if not rules:
        return ""

    profile = sport_profile(_row_value(tournament, "sport", "Fotboll"))
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


def render_public_view(tournament_id, tournament):
    track_public_visit(tournament_id)
    published_matches = all_rows(
        "SELECT * FROM matches WHERE tournament_id=? AND scheduled_start IS NOT NULL AND schedule_published=1 ORDER BY scheduled_start,pitch_number,id",
        (tournament_id,),
    )
    played_matches = [m for m in published_matches if m["home_score"] is not None and m["away_score"] is not None]
    total_goals = sum(int(m["home_score"] or 0) + int(m["away_score"] or 0) for m in played_matches)
    public_teams = all_rows("SELECT * FROM teams WHERE tournament_id=? ORDER BY name", (tournament_id,))
    team_count = len(public_teams)
    public_team_by_id = {row["id"]: row for row in public_teams}
    public_team_names = {row["id"]: row["name"] for row in public_teams}
    public_events_by_match = {}
    now = datetime.now()

    public_groups = all_rows(
        "SELECT id,name FROM groups WHERE tournament_id=? ORDER BY name",
        (tournament_id,),
    )

    def _public_source_team_id(source):
        """Lös vanliga team:<id>-källor lokalt; bara komplexa slutspelskällor behöver DB-resolver."""
        parts = source.split(":") if source else []
        if len(parts) >= 2 and parts[0] == "team":
            try:
                return int(parts[1])
            except (TypeError, ValueError):
                return None
        return resolve_source(source)

    def _public_source_label(source):
        team_id = _public_source_team_id(source)
        if team_id in public_team_names:
            return public_team_names[team_id]
        return source_label(source)
    filtered_public_matches = published_matches
    next_match = next(
        (
            m for m in filtered_public_matches
            if datetime.fromisoformat(m["scheduled_start"]) >= now and m["home_score"] is None
        ),
        None,
    )
    hero_meta = f"{cup_date_label(tournament)} · {html.escape(tournament['location'] or 'Spelort ej angiven')}"
    visitor_rows = []
    if tournament["arena_address"]:
        visitor_rows.append(f"<div><b>📍 Arena:</b> {html.escape(tournament['arena_address'])}</div>")
    if tournament["kiosk_information"]:
        kiosk_text = html.escape(tournament["kiosk_information"])
        visitor_rows.append(f"<div><b>☕ Kiosk:</b> {kiosk_text}</div>")
    else:
        visitor_rows.append("<div><b>☕ Kiosk:</b> Ingen kiosk har angetts.</div>")
    if tournament["public_information"]:
        public_text = html.escape(tournament["public_information"]).replace("\n", "<br>")
        visitor_rows.append(f"<div><b>ℹ️ Information:</b><br>{public_text}</div>")
    if tournament["organizer_phone"]:
        phone_display = html.escape(tournament["organizer_phone"])
        phone_href = re.sub(r"[^0-9+]", "", tournament["organizer_phone"])
        visitor_rows.append(
            "<div class='cn-organizer-contact'>"
            f"<div><b>📞 {html.escape(tr('Kontakta arrangören'))}</b></div>"
            f"<a class='cn-call-button' href='tel:{html.escape(phone_href)}'>☎ Ring {phone_display}</a>"
            "</div>"
        )
    if tournament["feedback_email"]:
        email_display = html.escape(tournament["feedback_email"])
        email_href = html.escape(tournament["feedback_email"], quote=True)
        visitor_rows.append(
            "<div class='cn-organizer-contact'>"
            f"<div><b>✉️ {html.escape(tr('Frågor eller feedback'))}</b></div>"
            f"<a class='cn-email-button' href='mailto:{email_href}?subject=CupNavi%20-%20{html.escape(tournament['name'], quote=True)}'>"
            f"✉ Skicka e-post till {email_display}</a>"
            "</div>"
        )
    if tournament["instagram_url"]:
        instagram_raw = tournament["instagram_url"].strip()
        if instagram_raw.startswith("@"):
            instagram_handle = instagram_raw[1:]
            instagram_href = f"https://www.instagram.com/{instagram_handle}/"
            instagram_label = f"@{instagram_handle}"
        elif instagram_raw.startswith("http://") or instagram_raw.startswith("https://"):
            instagram_href = instagram_raw
            instagram_label = instagram_raw.rstrip("/").split("/")[-1]
            instagram_label = f"@{instagram_label}" if instagram_label else "Instagram"
        else:
            instagram_handle = instagram_raw.strip("/")
            instagram_href = f"https://www.instagram.com/{instagram_handle}/"
            instagram_label = f"@{instagram_handle}"

        visitor_rows.append(
            "<div class='cn-organizer-contact'>"
            f"<div><b>📷 {html.escape(tr('Följ cupen'))}</b></div>"
            f"<a class='cn-instagram-button' href='{html.escape(instagram_href, quote=True)}' "
            "target='_blank' rel='noopener noreferrer'>"
            f"Instagram {html.escape(instagram_label)}</a>"
            "</div>"
        )

    st.markdown(
        f"""<div class='cup-hero'><div class='eyebrow'>CupNavi · {html.escape(tr("Turneringsöversikt"))}</div>
        <div class='title'>{html.escape(tournament['name'])}</div><div class='meta'>{hero_meta} · {html.escape(str(_row_value(tournament, 'sport', 'Fotboll')))}</div></div>""",
        unsafe_allow_html=True,
    )
    public_lifecycle = normalize_status(_row_value(tournament, "lifecycle_status", None), is_published=bool(tournament["is_published"]))
    if public_lifecycle == "completed":
        st.success("🏆 Avslutad cup · Resultat, tabeller, slutspel och statistik är arkiverade och finns kvar som historik.")
    elif public_lifecycle == "live":
        st.info("🔴 Cupen pågår")

    # Min cup: lagvalet ligger även i URL:en så länken kan bokmärkas/delas och
    # fungerar utan konto. Session state gör växlingen snabb under samma besök.
    team_query = st.query_params.get("team") if hasattr(st, "query_params") else None
    pitch_query = st.query_params.get("pitch") if hasattr(st, "query_params") else None
    try:
        requested_team_id = int(team_query) if team_query else None
    except (TypeError, ValueError):
        requested_team_id = None
    try:
        requested_pitch_no = int(pitch_query) if pitch_query else None
    except (TypeError, ValueError):
        requested_pitch_no = None
    if requested_team_id not in public_team_names:
        requested_team_id = None

    with st.container(border=True):
        min_cup_col1, min_cup_col2 = st.columns([3, 1])
        favorite_options = [None] + [row["id"] for row in public_teams]
        favorite_index = favorite_options.index(requested_team_id) if requested_team_id in favorite_options else 0
        favorite_team_id = min_cup_col1.selectbox(
            "⭐ Min cup – följ ett lag",
            favorite_options,
            index=favorite_index,
            format_func=lambda team_id: tr("Alla lag") if team_id is None else public_team_names.get(team_id, "Lag"),
            key=f"public_favorite_team_{tournament_id}",
        )
        if favorite_team_id is not None and favorite_team_id != requested_team_id:
            if hasattr(st, "query_params"):
                st.query_params["team"] = str(favorite_team_id)
                st.query_params["cup"] = str(tournament_id)
            st.rerun()
        if favorite_team_id is None and requested_team_id is not None:
            if hasattr(st, "query_params"):
                try:
                    del st.query_params["team"]
                except KeyError:
                    pass
                st.query_params["cup"] = str(tournament_id)
            st.rerun()
        if requested_team_id:
            if min_cup_col2.button(tr("Visa alla lag"), key=f"clear_favorite_team_{tournament_id}", use_container_width=True):
                if hasattr(st, "query_params"):
                    try:
                        del st.query_params["team"]
                    except KeyError:
                        pass
                st.rerun()
            favorite_matches = [
                m for m in published_matches
                if requested_team_id in (_public_source_team_id(m["home_source"]), _public_source_team_id(m["away_source"]))
            ]
            favorite_next = next((m for m in favorite_matches if m["home_score"] is None and datetime.fromisoformat(m["scheduled_start"]) >= now), None)
            notification_rows = all_rows(
                """SELECT * FROM notifications WHERE tournament_id=? AND (team_id=? OR team_id IS NULL)
                   ORDER BY created_at DESC,id DESC LIMIT 5""",
                (tournament_id, requested_team_id),
            )
            st.markdown(f"**{html.escape(public_team_names[requested_team_id])}** · {len(favorite_matches)} matcher")
            if favorite_next:
                st.caption(
                    f"Nästa: {_public_source_label(favorite_next['home_source'])} – {_public_source_label(favorite_next['away_source'])} · "
                    f"{swedish_datetime(favorite_next['scheduled_start'])} · Plan {favorite_next['pitch_number']}"
                )
            if notification_rows:
                with st.expander(f"🔔 Notiser ({len(notification_rows)})", expanded=False):
                    for note in notification_rows:
                        st.markdown(f"**{note['title']}**  \n{note['message']}")
                        st.caption(note["created_at"].replace("T", " "))
            st.caption("Tips: bokmärk den här sidan så öppnas CupNavi med ditt lag valt nästa gång.")

    share_state_key = f"public_share_open_{tournament_id}"
    share_is_open = bool(st.session_state.get(share_state_key, False))
    if st.button(
        ("✕ " + tr("Dölj delning")) if share_is_open else ("📤 " + tr("Dela cupen")),
        key=f"public_share_toggle_{tournament_id}",
    ):
        share_is_open = not share_is_open
        st.session_state[share_state_key] = share_is_open

    if share_is_open:
        with st.container(border=True):
            st.caption(tr("Dela länken eller QR-koden till den här cupen."))
            render_share_panel(tournament_id, tournament["name"])
            render_qr_share_panel(tournament_id, tournament["name"])

    public_page_key = f"public_page_v92_{tournament_id}"
    if public_page_key not in st.session_state:
        st.session_state[public_page_key] = "Matcher"

    nav1, nav2, nav3 = st.columns(3)
    main_nav = [
        (nav1, "Matcher", "🗓️", tr("Matcher")),
        (nav2, "Statistik", "🏆", tr("Tabell & statistik")),
        (nav3, "Info", "ℹ️", tr("Info")),
    ]
    for nav_col, page_value, icon, label in main_nav:
        active = st.session_state[public_page_key] == page_value
        if nav_col.button(
            f"{icon}  {label}",
            key=f"public_nav_v92_{tournament_id}_{page_value}",
            type="primary" if active else "secondary",
            use_container_width=True,
        ):
            st.session_state[public_page_key] = page_value
            st.rerun()

    public_page = st.session_state[public_page_key]

    def _filter_public_matches(base_matches, key_prefix, heading):
        """Gemensamt filter för den sammanslagna matchsidan."""
        st.markdown(f"#### {heading}")
        filter_mode = st.radio(
            tr("Vad vill du visa?"),
            [tr("Alla matcher"), tr("En grupp"), tr("Ett lag"), tr("En plan")],
            horizontal=True,
            key=f"{key_prefix}_mode_{tournament_id}",
            label_visibility="collapsed",
        )
        filtered = list(base_matches)
        filter_label = "Alla matcher"

        if filter_mode == tr("En grupp"):
            if public_groups:
                selected_group = st.selectbox(
                    tr("Välj grupp"),
                    [row["id"] for row in public_groups],
                    format_func=lambda group_id: next(
                        row["name"] for row in public_groups if row["id"] == group_id
                    ),
                    key=f"{key_prefix}_group_{tournament_id}",
                )
                filter_label = next(
                    row["name"] for row in public_groups if row["id"] == selected_group
                )
                filtered = [
                    match_row for match_row in base_matches
                    if match_row["group_id"] == selected_group
                ]
            else:
                filtered = []
                st.info("Det finns inga grupper att filtrera på.")

        elif filter_mode == tr("Ett lag"):
            if public_teams:
                selected_team = st.selectbox(
                    tr("Välj lag"),
                    [row["id"] for row in public_teams],
                    format_func=lambda team_id: next(
                        row["name"] for row in public_teams if row["id"] == team_id
                    ),
                    key=f"{key_prefix}_team_{tournament_id}",
                )
                filter_label = next(
                    row["name"] for row in public_teams if row["id"] == selected_team
                )
                filtered = [
                    match_row for match_row in base_matches
                    if (
                        _public_source_team_id(match_row["home_source"]) == selected_team
                        or _public_source_team_id(match_row["away_source"]) == selected_team
                    )
                ]
            else:
                filtered = []
                st.info("Det finns inga lag att filtrera på.")

        elif filter_mode == tr("En plan"):
            pitch_options = sorted({
                int(match_row["pitch_number"])
                for match_row in base_matches
                if match_row["pitch_number"] is not None
            })
            if pitch_options:
                selected_pitch = st.selectbox(
                    tr("Välj plan"),
                    pitch_options,
                    format_func=lambda pitch_no: f"Plan {pitch_no}",
                    key=f"{key_prefix}_pitch_{tournament_id}",
                )
                filter_label = f"Plan {selected_pitch}"
                filtered = [
                    match_row for match_row in base_matches
                    if int(match_row["pitch_number"] or 0) == selected_pitch
                ]
            else:
                filtered = []
                st.info("Det finns inga planer att filtrera på.")

        return (
            sorted(
                filtered,
                key=lambda match_row: (
                    match_row["scheduled_start"] or "",
                    match_row["pitch_number"] or 0,
                    match_row["id"],
                ),
            ),
            filter_mode,
            filter_label,
        )

    def _render_public_match_cards(matches, show_results=None, show_weather=False):
        """Ett gemensamt matchkort: spelade matcher visar resultat, kommande visar VS."""
        referees = {
            row["id"]: row["name"]
            for row in all_rows(
                "SELECT * FROM referees WHERE tournament_id=?",
                (tournament_id,),
            )
        }
        weather_forecast, weather_status = ({}, "")
        if show_weather:
            weather_forecast, weather_status = fetch_weather_forecast(tournament["location"] or "")

        st.markdown(
            """
            <style>
              .public-match-card,
              .public-match-card div,
              .public-match-card span,
              .public-match-card b { color:#172033 !important; }
              .public-match-card .match-stage { color:#ffffff !important; }
              .public-match-card .match-meta { color:#334155 !important; }
              .public-match-card .kit-label,
              .public-match-card .match-referee,
              .public-match-card .match-weather { color:#475569 !important; }
              .public-match-card .match-score { color:#0f172a !important; }
              .public-match-card .public-team-name { font-size:18px !important;line-height:1.25;font-weight:800; }
            </style>
            """,
            unsafe_allow_html=True,
        )

        if not matches:
            st.info("Inga matcher finns för det valda filtret.")
            return

        for number, match_row in enumerate(matches, 1):
            home = public_team_by_id.get(_public_source_team_id(match_row["home_source"]))
            away = public_team_by_id.get(_public_source_team_id(match_row["away_source"]))
            home_name = home["name"] if home else _public_source_label(match_row["home_source"])
            away_name = away["name"] if away else _public_source_label(match_row["away_source"])
            start = swedish_datetime(match_row["scheduled_start"])
            weather_text = ""
            if show_weather:
                match_weather = weather_for_match(weather_forecast, match_row["scheduled_start"])
                weather_text = weather_label(match_weather) if weather_forecast else weather_status

            _, _, away_kit_used = match_kit_colors(home, away)
            home_kit_bg = kit_background_for_team(home, "home") if home else "#94a3b8"
            away_selected_kit = "away" if away_kit_used else "home"
            away_kit_bg = kit_background_for_team(away, away_selected_kit) if away else "#94a3b8"

            match_is_played = match_row["home_score"] is not None and match_row["away_score"] is not None
            row_show_results = match_is_played if show_results is None else bool(show_results)

            if row_show_results:
                center_text = f"{match_row['home_score']}–{match_row['away_score']}"
                if match_row["home_penalties"] is not None:
                    center_text += f" ({match_row['home_penalties']}–{match_row['away_penalties']} str.)"
                status_text, status_class = "SLUT", "status-finished"
                match_events_html = public_match_events_html(
                    match_row["id"],
                    match_row=match_row,
                    rows=public_events_by_match.get(match_row["id"], []),
                    team_names=public_team_names,
                )
            else:
                center_text = "VS"
                match_events_html = ""
                match_start_dt = datetime.fromisoformat(match_row["scheduled_start"])
                if match_row["home_score"] is not None and match_row["away_score"] is not None:
                    status_text, status_class = "SPELAD", "status-finished"
                elif match_start_dt <= now <= match_start_dt + timedelta(hours=2):
                    status_text, status_class = "PÅGÅR", "status-live"
                else:
                    status_text, status_class = "KOMMANDE", "status-upcoming"

            st.markdown(
                f"""
                <div class="public-match-card" style="border:1px solid #d1d5db;border-radius:14px;padding:16px;margin:12px 0;background:linear-gradient(135deg,#ffffff,#f3f6fb);color:#172033;box-shadow:0 4px 12px rgba(15,23,42,.08)">
                  <div style="display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #e5e7eb;padding-bottom:9px">
                    <div style="display:flex;gap:7px;align-items:center"><span class="match-stage" style="font-size:12px;font-weight:700;color:#fff;background:#166534;padding:4px 9px;border-radius:999px">{match_row['stage']}</span><span class="status-pill {status_class}">{status_text}</span></div>
                    <span class="match-meta" style="font-size:13px;color:#334155">Match {number} · <b>{start}</b> · Plan {match_row['pitch_number']}</span>
                  </div>
                  <div style="display:grid;grid-template-columns:1fr auto 1fr;gap:15px;align-items:center;margin-top:8px;color:#0f172a">
                    <div><span style="display:inline-block;width:22px;height:15px;background:{home_kit_bg};border:1px solid #444;border-radius:3px"></span>
                    <b class="public-team-name">{html.escape(home_name)}</b><br><small class="kit-label">Hemmalagets hemmaställ</small></div>
                    <div class="match-score" style="font-size:20px;font-weight:700">{center_text}</div>
                    <div style="text-align:right"><b class="public-team-name">{html.escape(away_name)}</b> <span style="display:inline-block;width:22px;height:15px;background:{away_kit_bg};border:1px solid #444;border-radius:3px"></span>
                    <br><small class="kit-label">{'Bortalagets bortaställ' if away_kit_used else 'Bortalagets hemmaställ'}</small></div>
                  </div>
                  {match_events_html}
                  {f'<div class="match-weather" style="font-size:12px;text-align:center;margin-top:10px">{html.escape(weather_text)}</div>' if show_weather else ''}
                  <div class="match-referee" style="font-size:12px;text-align:center;margin-top:10px">Domare: {html.escape(referees.get(match_row['referee_id'], 'Ej tillsatt'))}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        if show_weather:
            st.caption("Väderprognos från Open-Meteo. Prognosen uppdateras automatiskt och kan förändras.")

    if public_page == "Matcher":
        feed_rows = all_rows(
            """SELECT * FROM cup_feed WHERE tournament_id=? AND public=1
               ORDER BY created_at DESC,id DESC LIMIT 8""",
            (tournament_id,),
        )
        if feed_rows:
            with st.expander("📣 Cupflöde", expanded=False):
                for item in feed_rows:
                    st.markdown(f"**{html.escape(item['title'])}**")
                    if item["detail"]:
                        st.caption(item["detail"])
                    st.caption(item["created_at"].replace("T", " "))

        st.markdown(
            f"""<div class='public-metric-grid'>
              <div class='public-metric'><div class='label'>{html.escape(tr("Lag"))}</div><div class='value'>{team_count}</div></div>
              <div class='public-metric'><div class='label'>{html.escape(tr("Matcher"))}</div><div class='value'>{len(published_matches)}</div></div>
              <div class='public-metric'><div class='label'>{html.escape(tr("Spelade"))}</div><div class='value'>{len(played_matches)}</div></div>
              <div class='public-metric'><div class='label'>{html.escape(str(sport_profile(_row_value(tournament, 'sport', 'Fotboll'))['score_label']).capitalize())}</div><div class='value'>{total_goals}</div></div>
            </div>""",
            unsafe_allow_html=True,
        )

        public_event_rows = all_rows(
            """
            SELECT s.match_id, p.name AS player_name, COALESCE(p.is_protected,0) AS is_protected,
                   t.id AS team_id, t.name AS team_name, s.goals, s.red_cards
            FROM player_match_stats s
            JOIN players p ON p.id=s.player_id
            JOIN teams t ON t.id=p.team_id
            JOIN matches m ON m.id=s.match_id
            WHERE m.tournament_id=? AND (s.goals > 0 OR s.red_cards > 0)
            ORDER BY s.match_id,p.name
            """,
            (tournament_id,),
        )
        public_events_by_match = {}
        for event_row in public_event_rows:
            public_events_by_match.setdefault(event_row["match_id"], []).append(event_row)

        match_view = st.segmented_control(
            tr("Visa matcher"),
            [tr("Alla"), tr("Kommande"), tr("Spelade")],
            default=tr("Alla"),
            key=f"public_match_view_{tournament_id}",
        ) or tr("Alla")

        if match_view == tr("Kommande"):
            base_match_list = [m for m in published_matches if m["home_score"] is None or m["away_score"] is None]
        elif match_view == tr("Spelade"):
            base_match_list = played_matches
        else:
            base_match_list = published_matches

        if requested_team_id:
            base_match_list = [
                m for m in base_match_list
                if requested_team_id in (_public_source_team_id(m["home_source"]), _public_source_team_id(m["away_source"]))
            ]
            st.info(f"⭐ Min cup visar matcher för {public_team_names[requested_team_id]}.")
        if requested_pitch_no:
            base_match_list = [m for m in base_match_list if int(m["pitch_number"] or 0) == requested_pitch_no]
            st.info(f"📍 QR-länken visar Plan {requested_pitch_no}.")

        match_list, match_filter_mode, match_filter_label = _filter_public_matches(
            base_match_list,
            "public_matches",
            tr("Filtrera matcher"),
        )
        st.caption(f"{tr('Visar')} {len(match_list)} {tr('matcher').lower()} · {match_filter_label}")

        upcoming_match = next(
            (
                match_row for match_row in match_list
                if match_row["home_score"] is None
                and datetime.fromisoformat(match_row["scheduled_start"]) >= now
            ),
            None,
        )
        if upcoming_match:
            next_home = _public_source_label(upcoming_match["home_source"])
            next_away = _public_source_label(upcoming_match["away_source"])
            if match_filter_mode == tr("Ett lag"):
                next_label = tr("Nästa match för valt lag")
            elif match_filter_mode == tr("En grupp"):
                next_label = tr("Nästa match i vald grupp")
            elif match_filter_mode == tr("En plan"):
                next_label = tr("Nästa match på vald plan")
            else:
                next_label = tr("Nästa match")
            st.markdown(
                f"""
                <div class="cn-next-match">
                  <div class="eyebrow">{html.escape(next_label)}</div>
                  <div class="teams">{html.escape(next_home)} – {html.escape(next_away)}</div>
                  <div class="meta">{swedish_datetime(upcoming_match['scheduled_start'])} · {html.escape(tr("Plan"))} {upcoming_match['pitch_number']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        show_match_weather = st.toggle(
            "🌦️ " + tr("Visa väderprognos"),
            value=False,
            key=f"public_matches_weather_{tournament_id}",
        )
        _render_public_match_cards(match_list, show_results=None, show_weather=show_match_weather)

    if public_page == "Statistik":
        stats_section = st.segmented_control(
            tr("Statistik"),
            [tr("Tabeller"), tr("Topplistor"), tr("Slutspel")],
            default=tr("Tabeller"),
            key=f"public_stats_section_{tournament_id}",
        ) or tr("Tabeller")

        if stats_section == tr("Tabeller"):
            groups = all_rows("SELECT * FROM groups WHERE tournament_id=? ORDER BY name", (tournament_id,))
            if not groups:
                st.info(tr("Inga grupper har publicerats ännu."))
            for group in groups:
                st.subheader(group["name"])
                group_table = calculate_table(group["id"], tournament)
                render_group_table(group_table, tournament)

        if stats_section == tr("Topplistor"):
            rows = all_rows(
                """
                SELECT CASE WHEN COALESCE(players.is_protected,0)=1 THEN 'Skyddad spelare' ELSE players.name END AS player_name,
                       teams.name AS team_name,
                       SUM(s.goals) AS goals,SUM(s.assists) AS assists,
                       SUM(s.yellow_cards) AS yellow_cards,SUM(s.red_cards) AS red_cards
                FROM player_match_stats s JOIN players ON players.id=s.player_id
                JOIN teams ON teams.id=players.team_id JOIN matches ON matches.id=s.match_id
                WHERE matches.tournament_id=? GROUP BY players.id,players.name,players.is_protected,teams.name
                """,
                (tournament_id,),
            )
            st.subheader(tr("Skytteliga"))
            goal_rows = [r for r in sorted(rows, key=lambda r: (-r["goals"], -r["assists"], r["player_name"].lower())) if int(r["goals"] or 0) > 0]
            if goal_rows:
                render_centered_table(pd.DataFrame([{"Pl": i, "Spelare": r["player_name"], "Lag": r["team_name"], "Mål": r["goals"]} for i, r in enumerate(goal_rows, 1)]))
            else:
                st.info(tr("Inga målskyttar har registrerats."))
            st.subheader(tr("Assistliga"))
            assist_rows = [r for r in sorted(rows, key=lambda r: (-r["assists"], -r["goals"], r["player_name"].lower())) if int(r["assists"] or 0) > 0]
            if assist_rows:
                render_centered_table(pd.DataFrame([{"Pl": i, "Spelare": r["player_name"], "Lag": r["team_name"], "Assist": r["assists"]} for i, r in enumerate(assist_rows, 1)]))
            else:
                st.info(tr("Inga assist har registrerats."))

            st.subheader(tr("Kortstatistik"))
            card_rows = [
                r for r in sorted(
                    rows,
                    key=lambda r: (-(int(r["yellow_cards"] or 0) + int(r["red_cards"] or 0)), -int(r["red_cards"] or 0), r["player_name"].lower()),
                )
                if int(r["yellow_cards"] or 0) > 0 or int(r["red_cards"] or 0) > 0
            ]
            if card_rows:
                render_centered_table(pd.DataFrame([
                    {
                        "Spelare": r["player_name"],
                        "Lag": r["team_name"],
                        "Gula": int(r["yellow_cards"] or 0),
                        "Röda": int(r["red_cards"] or 0),
                    }
                    for r in card_rows
                ]))
            else:
                st.info(tr("Inga kort har registrerats."))

        if stats_section == tr("Slutspel"):
            forecast_groups = all_rows("SELECT * FROM groups WHERE tournament_id=? ORDER BY name", (tournament_id,))
            forecast_tables = {group["name"]: calculate_table(group["id"], tournament) for group in forecast_groups}
            forecast_lines = playoff_preview(forecast_tables, tournament["playoff_format"])
            if forecast_lines:
                with st.expander("🔮 Slutspelsprognos – om tabellerna slutar så här", expanded=False):
                    st.caption("Prognosen bygger på tabelläget just nu och uppdateras när resultat registreras.")
                    for line in forecast_lines:
                        st.write(f"• {line}")
            brackets = [] if tournament["playoff_format"] == "Inget slutspel" else brackets_for_display(tournament_id)[0]
            if not brackets:
                st.info(tr("Turneringen har inget publicerat slutspel."))
            for bracket in brackets:
                st.subheader(bracket["name"])
                render_bracket_tree(bracket["id"], public=True)

    if public_page == "Info":
        info_rules = one_row("SELECT * FROM schedule_rules WHERE tournament_id=?", (tournament_id,))
        st.markdown(f"### 📘 {tr('Cupens regler')}")
        rules_html = public_rules_html(tournament, info_rules)
        if rules_html:
            st.markdown(rules_html, unsafe_allow_html=True)

        if tournament["public_information"]:
            st.markdown(f"### ✍️ {tr('Information från arrangören')}")
            public_text = html.escape(tournament["public_information"]).replace("\n", "<br>")
            st.markdown(f"<div class='cn-custom-info-card'>{public_text}</div>", unsafe_allow_html=True)

        st.markdown(f"### 📍 {tr('Praktisk information')}")
        practical_rows = []
        if tournament["arena_address"]:
            practical_rows.append(f"<div><b>📍 {html.escape(tr('Arena'))}:</b> {html.escape(tournament['arena_address'])}</div>")
        if tournament["kiosk_information"]:
            practical_rows.append(f"<div><b>☕ {html.escape(tr('Kiosk'))}:</b> {html.escape(tournament['kiosk_information'])}</div>")
        if tournament["organizer_phone"]:
            phone_display = html.escape(tournament["organizer_phone"])
            phone_href = re.sub(r"[^0-9+]", "", tournament["organizer_phone"])
            practical_rows.append(f"<div><b>📞 {html.escape(tr('Kontakt'))}:</b> <a href='tel:{html.escape(phone_href)}'>{phone_display}</a></div>")
        if tournament["feedback_email"]:
            email_display = html.escape(tournament["feedback_email"])
            email_href = html.escape(tournament["feedback_email"], quote=True)
            practical_rows.append(f"<div><b>✉️ E-post:</b> <a href='mailto:{email_href}'>{email_display}</a></div>")
        if tournament["instagram_url"]:
            instagram_raw = tournament["instagram_url"].strip()
            if instagram_raw.startswith("@"):
                instagram_handle = instagram_raw[1:]
                instagram_href = f"https://www.instagram.com/{instagram_handle}/"
                instagram_label = f"@{instagram_handle}"
            elif instagram_raw.startswith("http://") or instagram_raw.startswith("https://"):
                instagram_href = instagram_raw
                instagram_handle = instagram_raw.rstrip("/").split("/")[-1]
                instagram_label = f"@{instagram_handle}" if instagram_handle else "Instagram"
            else:
                instagram_handle = instagram_raw.strip("/")
                instagram_href = f"https://www.instagram.com/{instagram_handle}/"
                instagram_label = f"@{instagram_handle}"
            practical_rows.append(
                f"<div><b>📷 {html.escape(tr('Instagram'))}:</b> "
                f"<a href='{html.escape(instagram_href, quote=True)}' target='_blank' rel='noopener noreferrer'>"
                f"{html.escape(instagram_label)}</a></div>"
            )

        if practical_rows:
            st.markdown("<div class='cn-practical-info-card'>" + "".join(practical_rows) + "</div>", unsafe_allow_html=True)
        else:
            st.info(tr("Ingen praktisk information har publicerats ännu."))

        venue_rows = all_rows(
            """SELECT * FROM venue_points WHERE tournament_id=? ORDER BY sort_order,id""",
            (tournament_id,),
        )
        if venue_rows:
            st.markdown("### 🗺️ Cupkarta")
            venue_icon = {"Plan": "🏟️", "Kiosk": "☕", "Toalett": "🚻", "Parkering": "🚗", "Sjukvård": "🩹", "Sekretariat": "ℹ️"}
            for point in venue_rows:
                icon = venue_icon.get(point["kind"], "📍")
                line = f"**{icon} {point['label']}**"
                if point["detail"]:
                    line += f"  \n{point['detail']}"
                st.markdown(line)
                if point["url"]:
                    st.markdown(f"[Öppna karta/länk]({point['url']})")

        all_public_matches = published_matches
        if all_public_matches and all(m["home_score"] is not None and m["away_score"] is not None for m in all_public_matches):
            top_scorer_row = one_row(
                """SELECT CASE WHEN COALESCE(players.is_protected,0)=1 THEN 'Skyddad spelare' ELSE players.name END AS player_name,
                          teams.name AS team_name,SUM(s.goals) AS goals
                   FROM player_match_stats s JOIN players ON players.id=s.player_id
                   JOIN teams ON teams.id=players.team_id JOIN matches ON matches.id=s.match_id
                   WHERE matches.tournament_id=? GROUP BY players.id,players.name,players.is_protected,teams.name
                   ORDER BY goals DESC,player_name LIMIT 1""",
                (tournament_id,),
            )
            summary = cup_summary(tournament, public_teams, all_public_matches, top_scorer_row)
            with st.expander("🏁 Cupsummering", expanded=False):
                st.markdown(
                    f"**{html.escape(summary['name'])}** · {summary['sport']}  \n"
                    f"{summary['teams']} deltagare/lag · {summary['played_matches']} spelade matcher · "
                    f"{summary['total_score']} registrerade {sport_profile(summary['sport'])['score_label']}"
                )
                if summary.get("top_scorer") and summary.get("top_scorer_score", 0) > 0:
                    st.caption(f"Toppscorer: {summary['top_scorer']} ({summary['top_scorer_team']}) – {summary['top_scorer_score']}")

        public_team_contacts = []
        if bool(_row_value(tournament, "allow_team_public_contact", 0)):
            public_team_contacts = all_rows(
                """SELECT name,public_contact_name,public_contact_phone,public_contact_email
                   FROM teams WHERE tournament_id=? AND public_contact_enabled=1
                   AND COALESCE(responsible_contact_protected,1)=0
                   AND (COALESCE(public_contact_name,'')<>'' OR COALESCE(public_contact_phone,'')<>'' OR COALESCE(public_contact_email,'')<>'')
                   ORDER BY name""",
                (tournament_id,),
            )
        if public_team_contacts:
            with st.expander("📞 Lagkontakter"):
                for contact in public_team_contacts:
                    bits = [x for x in (contact["public_contact_name"], contact["public_contact_phone"], contact["public_contact_email"]) if x]
                    st.markdown(f"**{html.escape(contact['name'])}** · " + " · ".join(html.escape(str(x)) for x in bits))

        public_functionaries = all_rows(
            """SELECT * FROM functionaries
               WHERE tournament_id=? AND active=1 AND public_contact=1
               ORDER BY role,name""",
            (tournament_id,),
        )
        if public_functionaries:
            with st.expander("👥 " + tr("Funktionärer")):
                for person in public_functionaries:
                    contact_bits = [bit for bit in (person["phone"], person["email"]) if bit]
                    pitch_text = f" · {tr('Plan')} {person['pitch_number']}" if person["pitch_number"] else ""
                    st.markdown(
                        f"**{html.escape(person['role'])}: {html.escape(person['name'])}**"
                        f"{pitch_text}"
                        + (f" · {' · '.join(html.escape(x) for x in contact_bits)}" if contact_bits else "")
                    )

        public_offers = all_rows(
            """SELECT * FROM offers WHERE tournament_id=? AND active=1 ORDER BY sort_order,id""",
            (tournament_id,),
        )
        if public_offers:
            with st.expander("🎁 " + tr("Erbjudanden")):
                for offer in public_offers:
                    business = f" · {offer['business_name']}" if offer["business_name"] else ""
                    st.markdown(f"**{html.escape(offer['title'])}**{html.escape(business)}")
                    if offer["description"]:
                        st.write(offer["description"])
                    if offer["discount_code"]:
                        st.caption(tr("Rabattkod"))
                        st.code(offer["discount_code"], language=None)
                    if offer["valid_until"]:
                        st.caption(f"{tr('Gäller t.o.m.')} {offer['valid_until']}")
                    if offer["url"]:
                        st.markdown(
                            f"<a href='{html.escape(offer['url'], quote=True)}' target='_blank' "
                            f"rel='noopener noreferrer'><b>{html.escape(tr('Öppna erbjudandet'))} ↗</b></a>",
                            unsafe_allow_html=True,
                        )

        public_sponsors = all_rows(
            """SELECT * FROM sponsors WHERE tournament_id=? AND active=1 ORDER BY sort_order,id""",
            (tournament_id,),
        )
        if public_sponsors:
            with st.expander("🤝 " + tr("Partners")):
                for sponsor in public_sponsors:
                    logo_html = (
                        f"<img src='{sponsor['logo_data_uri']}' alt='' style='max-width:140px;max-height:70px;object-fit:contain;margin:4px 0 8px'>"
                        if sponsor["logo_data_uri"] else ""
                    )
                    level_html = f"<div style='font-size:12px;font-weight:800;color:#166534'>{html.escape(sponsor['level'])}</div>" if sponsor["level"] else ""
                    website_html = (
                        f"<div style='margin-top:7px'><a href='{html.escape(sponsor['website_url'], quote=True)}' target='_blank' rel='noopener noreferrer'>"
                        f"{html.escape(tr('Besök partnern'))} ↗</a></div>"
                        if sponsor["website_url"] else ""
                    )
                    description_html = f"<div style='margin-top:6px'>{html.escape(sponsor['description'])}</div>" if sponsor["description"] else ""
                    st.markdown(
                        f"<div style='padding:10px 0'>{logo_html}{level_html}<b>{html.escape(sponsor['name'])}</b>{description_html}{website_html}</div>",
                        unsafe_allow_html=True,
                    )

        with st.expander("💬 " + tr("Rapportera problem eller lämna synpunkt")):
            st.caption(tr("Feedbacken sparas till den här turneringen och kan läsas av administratören."))
            with st.form(f"public_feedback_{tournament_id}", clear_on_submit=True):
                feedback_area = st.selectbox(
                    tr("Vad gäller det?"),
                    [tr("Matcher"), tr("Tabeller"), tr("Topplistor"), tr("Slutspel"), tr("Info"), tr("Mobil/utseende"), tr("Annat")],
                )
                feedback_message = st.text_area(tr("Beskriv problemet eller synpunkten"), max_chars=2000)
                feedback_contact = st.text_input(tr("Kontaktuppgift (frivilligt)"), max_chars=200)
                if st.form_submit_button(tr("Skicka feedback")):
                    if not feedback_message.strip():
                        st.error(tr("Skriv en kort beskrivning först."))
                    else:
                        run(
                            "INSERT INTO feedback(tournament_id,created_at,area,message,contact) VALUES(?,?,?,?,?)",
                            (tournament_id, datetime.now().isoformat(timespec="seconds"), feedback_area,
                             feedback_message.strip(), feedback_contact.strip() or None),
                        )
                        st.success(tr("Tack. Feedbacken är sparad."))


def render_match_reporter_view(tournament_id, tournament):
    """Begränsad arbetsyta: endast resultat och matchhändelser."""
    st.title(f"📝 Matchrapportör · {tournament['name']}")
    st.caption(
        "Här kan du endast rapportera resultat samt mål, assist, varningar och utvisningar. "
        "Övrig administration är inte tillgänglig."
    )

    result_tab, event_tab, referee_tab, offline_tab = st.tabs([
        tr("CupNavi Score"), tr("Matchhändelser"), tr("Domarcentral"), tr("Offlineutkast")
    ])

    with result_tab:
        matches = all_rows(
            """SELECT * FROM matches
               WHERE tournament_id=? AND scheduled_start IS NOT NULL
               ORDER BY scheduled_start,pitch_number,id""",
            (tournament_id,),
        )
        playable_matches = [
            match_row for match_row in matches
            if resolve_source(match_row["home_source"]) and resolve_source(match_row["away_source"])
        ]

        if "reporter_result_message" in st.session_state:
            st.success(st.session_state.pop("reporter_result_message"), icon="✅")

        if not playable_matches:
            st.info("Det finns ännu inga schemalagda matcher med två klara lag.")
        else:
            st.markdown("### ⚡ CupNavi Score")
            quick_match_id = st.selectbox(
                "Välj match för snabbresultat",
                [row["id"] for row in playable_matches],
                format_func=lambda match_id: match_result_label(next(row for row in playable_matches if row["id"] == match_id)),
                key=f"quick_score_match_{tournament_id}",
            )
            quick_match = next(row for row in playable_matches if row["id"] == quick_match_id)
            quick_home_name = source_label(quick_match["home_source"])
            quick_away_name = source_label(quick_match["away_source"])
            draft_key = f"quick_score_draft_{quick_match_id}"
            if draft_key not in st.session_state:
                st.session_state[draft_key] = [int(quick_match["home_score"] or 0), int(quick_match["away_score"] or 0)]
            quick_home_score, quick_away_score = st.session_state[draft_key]
            qh, qc, qa = st.columns([2, 1, 2])
            qh.markdown(f"**{quick_home_name}**")
            qa.markdown(f"**{quick_away_name}**")
            qh_minus, qh_plus = qh.columns(2)
            qa_minus, qa_plus = qa.columns(2)
            if qh_minus.button("−", key=f"qs_hm_{quick_match_id}", use_container_width=True):
                st.session_state[draft_key][0] = max(0, quick_home_score - 1); st.rerun()
            if qh_plus.button("+", key=f"qs_hp_{quick_match_id}", use_container_width=True):
                st.session_state[draft_key][0] = quick_home_score + 1; st.rerun()
            if qa_minus.button("−", key=f"qs_am_{quick_match_id}", use_container_width=True):
                st.session_state[draft_key][1] = max(0, quick_away_score - 1); st.rerun()
            if qa_plus.button("+", key=f"qs_ap_{quick_match_id}", use_container_width=True):
                st.session_state[draft_key][1] = quick_away_score + 1; st.rerun()
            qc.markdown(
                f"<div style='text-align:center;font-size:30px;font-weight:900;padding-top:8px'>{quick_home_score}–{quick_away_score}</div>",
                unsafe_allow_html=True,
            )
            save_col, reset_col = st.columns(2)
            playoff_tie_needs_detail = quick_match["stage"] != "Gruppspel" and quick_home_score == quick_away_score
            if save_col.button(
                "✅ Spara slutresultat", key=f"qs_save_{quick_match_id}", type="primary", use_container_width=True,
                disabled=playoff_tie_needs_detail,
            ):
                before = {"home_score": quick_match["home_score"], "away_score": quick_match["away_score"]}
                run("UPDATE matches SET home_score=?,away_score=? WHERE id=?", (quick_home_score, quick_away_score, quick_match_id))
                description = f"{quick_home_name}–{quick_away_name} {quick_home_score}–{quick_away_score}"
                record_audit(tournament_id, "result", "match", description, entity_id=quick_match_id, before=before,
                             after={"home_score": quick_home_score, "away_score": quick_away_score}, actor="Matchrapportör")
                add_feed_item(tournament_id, f"Slut: {description}", category="Resultat", related_match_id=quick_match_id)
                for team_id in _match_team_ids(quick_match):
                    add_team_notification(tournament_id, team_id, "Nytt resultat", description, event_key=f"result:{quick_match_id}:{quick_home_score}:{quick_away_score}")
                st.session_state["reporter_result_message"] = "Slutresultatet är sparat."
                st.rerun()
            if reset_col.button("Återställ utkast", key=f"qs_reset_{quick_match_id}", use_container_width=True):
                st.session_state[draft_key] = [int(quick_match["home_score"] or 0), int(quick_match["away_score"] or 0)]; st.rerun()
            if playoff_tie_needs_detail:
                st.info("Oavgjord slutspelsmatch behöver avgörande uppgifter. Använd tabellen nedan för straffar/lottning.")
            st.divider()
            st.caption("Tabellen nedan finns kvar för massinmatning och slutspelsavgöranden.")

            team_rows = all_rows(
                "SELECT id,name FROM teams WHERE tournament_id=? ORDER BY name",
                (tournament_id,),
            )
            team_name_by_id = {row["id"]: row["name"] for row in team_rows}
            team_id_by_name = {row["name"]: row["id"] for row in team_rows}
            decision_options = ["–"] + [row["name"] for row in team_rows]

            result_rows = []
            for match_row in playable_matches:
                result_rows.append({
                    "match_id": match_row["id"],
                    "Match": swedish_datetime(match_row["scheduled_start"]),
                    "Plan": match_row["pitch_number"],
                    "Fas": match_row["stage"],
                    "Hemmalag": source_label(match_row["home_source"]),
                    "Hemmamål": match_row["home_score"],
                    "Bortamål": match_row["away_score"],
                    "Bortalag": source_label(match_row["away_source"]),
                    "Hemmastraffar": match_row["home_penalties"] if match_row["stage"] != "Gruppspel" else None,
                    "Bortastraffar": match_row["away_penalties"] if match_row["stage"] != "Gruppspel" else None,
                    "Avgörande vinnare": (
                        team_name_by_id.get(match_row["decided_winner_id"], "–")
                        if match_row["stage"] != "Gruppspel" else "–"
                    ),
                })

            edited_results = st.data_editor(
                pd.DataFrame(result_rows),
                hide_index=True,
                use_container_width=True,
                disabled=["match_id", "Match", "Plan", "Fas", "Hemmalag", "Bortalag"],
                column_order=[
                    "Match", "Plan", "Fas", "Hemmalag", "Hemmamål",
                    "Bortamål", "Bortalag", "Hemmastraffar",
                    "Bortastraffar", "Avgörande vinnare",
                ],
                column_config={
                    "Hemmamål": st.column_config.NumberColumn(min_value=0, max_value=99, step=1),
                    "Bortamål": st.column_config.NumberColumn(min_value=0, max_value=99, step=1),
                    "Hemmastraffar": st.column_config.NumberColumn(
                        "Straffar hemma", min_value=0, max_value=99, step=1
                    ),
                    "Bortastraffar": st.column_config.NumberColumn(
                        "Straffar borta", min_value=0, max_value=99, step=1
                    ),
                    "Avgörande vinnare": st.column_config.SelectboxColumn(options=decision_options),
                },
                key=f"reporter_results_{tournament_id}",
            )

            original_by_id = {int(row["id"]): row for row in playable_matches}
            updates = []
            info_messages = []
            error_messages = []

            for _, row in edited_results.iterrows():
                match_id = int(row["match_id"])
                original = original_by_id[match_id]
                home_score = None if pd.isna(row["Hemmamål"]) else int(row["Hemmamål"])
                away_score = None if pd.isna(row["Bortamål"]) else int(row["Bortamål"])
                home_penalties = None if pd.isna(row["Hemmastraffar"]) else int(row["Hemmastraffar"])
                away_penalties = None if pd.isna(row["Bortastraffar"]) else int(row["Bortastraffar"])
                selected_decided = team_id_by_name.get(row["Avgörande vinnare"])

                changed = any([
                    home_score != original["home_score"],
                    away_score != original["away_score"],
                    home_penalties != original["home_penalties"],
                    away_penalties != original["away_penalties"],
                    (
                        row["Fas"] != "Gruppspel"
                        and row["Avgörande vinnare"] != "–"
                        and selected_decided != original["decided_winner_id"]
                    ),
                ])
                if not changed:
                    continue

                if (home_score is None) != (away_score is None):
                    info_messages.append(
                        f"{row['Hemmalag']}–{row['Bortalag']}: fyll i båda målresultaten."
                    )
                    continue

                decided_winner_id = None
                if row["Fas"] == "Gruppspel":
                    home_penalties = None
                    away_penalties = None
                elif home_score is not None and home_score == away_score:
                    home_team_id = team_id_by_name.get(row["Hemmalag"])
                    away_team_id = team_id_by_name.get(row["Bortalag"])

                    if tournament["playoff_tie_rule"] == "Lottning":
                        home_penalties = None
                        away_penalties = None
                        if selected_decided in (home_team_id, away_team_id):
                            decided_winner_id = selected_decided
                        else:
                            info_messages.append(
                                f"{row['Hemmalag']}–{row['Bortalag']}: välj vinnare av lottningen."
                            )
                    else:
                        if home_penalties is not None or away_penalties is not None:
                            if (
                                home_penalties is None
                                or away_penalties is None
                                or home_penalties == away_penalties
                            ):
                                error_messages.append(
                                    f"{row['Hemmalag']}–{row['Bortalag']}: ange ett komplett avgörande straffresultat."
                                )
                                continue
                        else:
                            info_messages.append(
                                f"{row['Hemmalag']}–{row['Bortalag']}: ange straffresultat för att avgöra matchen."
                            )
                else:
                    home_penalties = None
                    away_penalties = None

                updates.append((
                    home_score,
                    away_score,
                    home_penalties,
                    away_penalties,
                    decided_winner_id,
                    match_id,
                ))

            for message in error_messages:
                st.error(message)
            for message in info_messages:
                st.info(message)

            if updates:
                with db() as con:
                    con.executemany(
                        """UPDATE matches
                           SET home_score=?,away_score=?,home_penalties=?,away_penalties=?,decided_winner_id=?
                           WHERE id=?""",
                        updates,
                    )
                    con.commit()
                _clear_render_query_cache()
                for home_score, away_score, home_penalties, away_penalties, decided_winner_id, changed_match_id in updates:
                    if home_score is None or away_score is None:
                        continue
                    changed_match = original_by_id[changed_match_id]
                    description = f"{source_label(changed_match['home_source'])}–{source_label(changed_match['away_source'])} {home_score}–{away_score}"
                    if home_penalties is not None and away_penalties is not None:
                        description += f" ({home_penalties}–{away_penalties} str.)"
                    add_feed_item(tournament_id, f"Slut: {description}", category="Resultat", related_match_id=changed_match_id)
                    for team_id in _match_team_ids(changed_match):
                        add_team_notification(tournament_id, team_id, "Nytt resultat", description,
                                              event_key=f"result:{changed_match_id}:{home_score}:{away_score}:{home_penalties}:{away_penalties}")
                st.session_state["_validation_dirty"] = True
                st.session_state["reporter_result_message"] = "Sparat automatiskt"
                st.rerun()

            st.caption("✓ Kompletta resultat sparas automatiskt.")

    with event_tab:
        played_matches = all_rows(
            """SELECT * FROM matches
               WHERE tournament_id=? AND home_score IS NOT NULL AND away_score IS NOT NULL
               ORDER BY scheduled_start DESC,id DESC""",
            (tournament_id,),
        )
        playable_matches = [
            match_row for match_row in played_matches
            if resolve_source(match_row["home_source"]) and resolve_source(match_row["away_source"])
        ]

        if not playable_matches:
            st.info("Rapportera först ett matchresultat. Därefter kan matchhändelser registreras.")
        else:
            match_id = st.selectbox(
                "Välj match",
                [row["id"] for row in playable_matches],
                format_func=lambda selected_id: match_result_label(
                    next(row for row in playable_matches if row["id"] == selected_id)
                ),
                key=f"reporter_event_match_{tournament_id}",
            )
            match_row = next(row for row in playable_matches if row["id"] == match_id)
            home_team_id = resolve_source(match_row["home_source"])
            away_team_id = resolve_source(match_row["away_source"])

            for selected_team_id in [home_team_id, away_team_id]:
                selected_team = team(selected_team_id)
                registered_match_roster = all_rows(
                    """SELECT p.* FROM players p
                       JOIN match_rosters mr ON mr.player_id=p.id
                       WHERE mr.match_id=? AND mr.team_id=? AND p.team_id=?
                       ORDER BY p.player_number,p.name""",
                    (match_id, selected_team_id, selected_team_id),
                )
                players = registered_match_roster or all_rows(
                    "SELECT * FROM players WHERE team_id=? ORDER BY player_number,name",
                    (selected_team_id,),
                )
                st.markdown(f"#### {selected_team['name']}")
                if registered_match_roster:
                    st.caption(f"Matchtrupp registrerad · {len(registered_match_roster)} spelare. Endast dessa kan få matchhändelser.")
                elif players:
                    st.warning("Matchtrupp saknas. Alla spelare visas tills en matchtrupp registreras.")
                if not players:
                    st.warning("Laget saknar registrerade spelare.")
                    continue

                existing = {
                    row["player_id"]: row
                    for row in all_rows(
                        """SELECT * FROM player_match_stats
                           WHERE match_id=? AND player_id IN
                           (SELECT id FROM players WHERE team_id=?)""",
                        (match_id, selected_team_id),
                    )
                }

                data = pd.DataFrame([
                    {
                        "player_id": player["id"],
                        "Nr": player["player_number"],
                        "Spelare": player["name"],
                        "Mål": existing[player["id"]]["goals"] if player["id"] in existing else 0,
                        "Assist": existing[player["id"]]["assists"] if player["id"] in existing else 0,
                        "Varningar": existing[player["id"]]["yellow_cards"] if player["id"] in existing else 0,
                        "Utvisningar": existing[player["id"]]["red_cards"] if player["id"] in existing else 0,
                    }
                    for player in players
                ])

                edited = st.data_editor(
                    data,
                    hide_index=True,
                    use_container_width=True,
                    disabled=["player_id", "Nr", "Spelare"],
                    column_order=["Nr", "Spelare", "Mål", "Assist", "Varningar", "Utvisningar"],
                    column_config={
                        "Mål": st.column_config.NumberColumn(min_value=0, step=1),
                        "Assist": st.column_config.NumberColumn(min_value=0, step=1),
                        "Varningar": st.column_config.NumberColumn(min_value=0, step=1),
                        "Utvisningar": st.column_config.NumberColumn(min_value=0, step=1),
                    },
                    key=f"reporter_stats_{match_id}_{selected_team_id}",
                )

                team_goals = int(
                    match_row["home_score"] if selected_team_id == home_team_id
                    else match_row["away_score"]
                )
                entered_goals = int(edited["Mål"].fillna(0).sum())
                entered_assists = int(edited["Assist"].fillna(0).sum())
                validation = validate_match_event_totals(
                    team_goals, entered_goals, entered_assists
                )
                for message in validation["errors"]:
                    st.error(f"{selected_team['name']}: {message}")

                autosave_key = f"reporter_event_saved_{match_id}_{selected_team_id}"
                if autosave_key in st.session_state:
                    st.success(st.session_state.pop(autosave_key), icon="✅")

                if not validation["errors"]:
                    changed_rows = []
                    for _, edited_row in edited.iterrows():
                        player_id = int(edited_row["player_id"])
                        new_values = (
                            int(edited_row["Mål"] or 0),
                            int(edited_row["Assist"] or 0),
                            int(edited_row["Varningar"] or 0),
                            int(edited_row["Utvisningar"] or 0),
                        )
                        previous = existing.get(player_id)
                        old_values = (
                            int(previous["goals"] or 0),
                            int(previous["assists"] or 0),
                            int(previous["yellow_cards"] or 0),
                            int(previous["red_cards"] or 0),
                        ) if previous else (0, 0, 0, 0)

                        if new_values != old_values:
                            changed_rows.append((player_id, *new_values))

                    if changed_rows:
                        with db() as con:
                            for player_id, goals, assists, yellows, reds in changed_rows:
                                con.execute(
                                    """INSERT INTO player_match_stats(
                                           match_id,player_id,goals,assists,yellow_cards,red_cards
                                       ) VALUES(?,?,?,?,?,?)
                                       ON CONFLICT(match_id,player_id) DO UPDATE SET
                                           goals=excluded.goals,
                                           assists=excluded.assists,
                                           yellow_cards=excluded.yellow_cards,
                                           red_cards=excluded.red_cards""",
                                    (match_id, player_id, goals, assists, yellows, reds),
                                )
                            con.commit()
                        _clear_render_query_cache()
                        st.session_state[autosave_key] = "Sparat automatiskt"
                        st.rerun()

                st.caption(
                    f"Matchresultat: {team_goals} mål · registrerade spelarmål: {entered_goals} · "
                    f"registrerade assist: {entered_assists}"
                )

    with referee_tab:
        st.markdown("### 🧑‍⚖️ Domarcentral")
        st.caption("Domare kan se sitt dagsprogram och bekräfta att uppdraget är sett. Ingen adminnavigation visas här.")
        referee_rows = all_rows("SELECT * FROM referees WHERE tournament_id=? ORDER BY name", (tournament_id,))
        if not referee_rows:
            st.info("Inga domare är registrerade.")
        else:
            referee_id = st.selectbox(
                "Välj domare",
                [row["id"] for row in referee_rows],
                format_func=lambda rid: next(row["name"] for row in referee_rows if row["id"] == rid),
                key=f"reporter_referee_{tournament_id}",
            )
            assignments = all_rows(
                """SELECT * FROM matches WHERE tournament_id=? AND referee_id=? AND scheduled_start IS NOT NULL
                   ORDER BY scheduled_start,pitch_number,id""",
                (tournament_id, referee_id),
            )
            acked = {
                row["match_id"] for row in all_rows(
                    "SELECT match_id FROM referee_acknowledgements WHERE tournament_id=? AND referee_id=?",
                    (tournament_id, referee_id),
                )
            }
            if not assignments:
                st.info("Domaren har inga schemalagda matcher ännu.")
            for assignment in assignments:
                with st.container(border=True):
                    st.markdown(
                        f"**{swedish_datetime(assignment['scheduled_start'])} · Plan {assignment['pitch_number']}**  \n"
                        f"{source_label(assignment['home_source'])} – {source_label(assignment['away_source'])}"
                    )
                    if assignment["id"] in acked:
                        st.success("Uppdraget är bekräftat.", icon="✅")
                    elif st.button("Bekräfta att jag sett matchen", key=f"ref_ack_{referee_id}_{assignment['id']}", use_container_width=True):
                        run(
                            """INSERT INTO referee_acknowledgements(tournament_id,referee_id,match_id,acknowledged_at)
                               VALUES(?,?,?,?) ON CONFLICT(referee_id,match_id) DO NOTHING""",
                            (tournament_id, referee_id, assignment["id"], datetime.now().isoformat(timespec="seconds")),
                        )
                        record_audit(tournament_id, "referee_ack", "match", "Domaruppdrag bekräftat", entity_id=assignment["id"], actor="Domare")
                        st.rerun()

    with offline_tab:
        st.markdown("### 📶 Offlineutkast")
        st.caption(
            "Streamlit kräver serverkontakt för riktig synkronisering. Den här säkerhetsfunktionen sparar därför ett lokalt "
            "resultatutkast i webbläsaren om nätet blir dåligt. Utkastet ligger kvar på enheten och kan föras över till CupNavi Score när nätet återkommer."
        )
        offline_matches = all_rows(
            """SELECT * FROM matches WHERE tournament_id=? AND scheduled_start IS NOT NULL ORDER BY scheduled_start,pitch_number,id""",
            (tournament_id,),
        )
        offline_options = [
            {
                "id": int(row["id"]),
                "label": f"{swedish_datetime(row['scheduled_start'])} · Plan {row['pitch_number']} · {source_label(row['home_source'])} – {source_label(row['away_source'])}",
            }
            for row in offline_matches
        ]
        offline_html = f"""
        <style>body{{font-family:Arial,sans-serif;color:#172033;margin:0}} .box{{border:1px solid #cbd5e1;border-radius:14px;padding:14px;background:#fff}}
        select,input,button{{font-size:16px;padding:9px;border:1px solid #cbd5e1;border-radius:9px}} .scores{{display:flex;gap:8px;margin:12px 0;align-items:center}} input{{width:70px}} button{{cursor:pointer;background:#ecfdf5}} #status{{font-size:12px;color:#475569;margin-top:8px}}</style>
        <div class='box'><b>Lokalt resultatutkast</b><br><small>Data sparas endast i den här webbläsaren.</small><br><br>
        <select id='m'></select><div class='scores'><input id='h' type='number' min='0' value='0'><b>–</b><input id='a' type='number' min='0' value='0'><button id='save'>Spara lokalt</button><button id='copy'>Kopiera</button></div><div id='status'></div></div>
        <script>
        const matches={json.dumps(offline_options, ensure_ascii=False)}; const key='cupnavi-offline-{int(tournament_id)}';
        const select=document.getElementById('m'); const h=document.getElementById('h'); const a=document.getElementById('a'); const status=document.getElementById('status');
        matches.forEach(x=>{{const o=document.createElement('option');o.value=x.id;o.textContent=x.label;select.appendChild(o)}});
        function load(){{const all=JSON.parse(localStorage.getItem(key)||'{{}}');const d=all[select.value];if(d){{h.value=d.h;a.value=d.a;status.textContent='Lokalt utkast hittat: '+d.saved}}else{{h.value=0;a.value=0;status.textContent='Inget lokalt utkast för vald match.'}}}}
        select.addEventListener('change',load); document.getElementById('save').onclick=()=>{{const all=JSON.parse(localStorage.getItem(key)||'{{}}');all[select.value]={{h:+h.value||0,a:+a.value||0,saved:new Date().toLocaleString()}};localStorage.setItem(key,JSON.stringify(all));status.textContent='Sparat lokalt på enheten.'}};
        document.getElementById('copy').onclick=async()=>{{const label=select.options[select.selectedIndex]?.text||'';const txt=label+' | '+h.value+'–'+a.value;try{{await navigator.clipboard.writeText(txt);status.textContent='Utkastet kopierades.'}}catch(e){{status.textContent=txt}}}}; load();
        </script>
        """
        components.html(offline_html, height=210, scrolling=False)


def _participant_role_label(tournament):
    sport = str(_row_value(tournament, "sport", "Fotboll") or "Fotboll")
    return "Spelare/Paransvarig" if sport in {"Tennis", "Padel"} else "Lagledare"


def _portal_match_label(match_row):
    when = swedish_datetime(match_row["scheduled_start"]) if match_row["scheduled_start"] else "Tid ej satt"
    pitch = f"Plan {match_row['pitch_number']}" if match_row["pitch_number"] else "Plan ej satt"
    return f"{when} · {pitch} · {source_label(match_row['home_source'])} – {source_label(match_row['away_source'])}"


def _save_match_roster(match_id, team_id, player_ids, actor="Deltagaransvarig"):
    selected_at = datetime.now().isoformat(timespec="seconds")
    with db() as con:
        con.execute("DELETE FROM match_rosters WHERE match_id=? AND team_id=?", (match_id, team_id))
        for player_id in player_ids:
            con.execute(
                "INSERT INTO match_rosters(match_id,team_id,player_id,selected_at,selected_by) VALUES(?,?,?,?,?)",
                (match_id, team_id, int(player_id), selected_at, actor),
            )
        con.commit()
    _clear_render_query_cache()


def render_team_portal(tournament_id, tournament):
    """Begränsad portal för ett enda lag/deltagare i en enda cup."""
    role_label = _participant_role_label(tournament)
    st.title(f"👥 {role_label} · {tournament['name']}")
    st.caption("Portalen ger endast åtkomst till det egna laget/deltagaren. Resultat och officiella matchhändelser rapporteras av matchrapportör eller domare.")

    teams = all_rows("SELECT * FROM teams WHERE tournament_id=? ORDER BY name", (tournament_id,))
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
            credential = one_row(
                "SELECT * FROM participant_access_credentials WHERE tournament_id=? AND team_id=?",
                (tournament_id, selected_team_id),
            )
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
    top1.success(f"Inloggad: {team_row['name']}")
    if top2.button("Logga ut", key=f"participant_logout_{tournament_id}_{team_id}", use_container_width=True):
        st.session_state.pop("participant_portal_auth", None)
        st.rerun()

    portal_tabs = st.tabs(["Översikt", "Trupp", "Matchtrupper", "Meddelanden"])

    with portal_tabs[0]:
        st.subheader("Lagstatus")
        c1, c2 = st.columns(2)
        if bool(team_row["checked_in"]):
            c1.success(f"✅ Incheckad {team_row['checked_in_at'] or ''}" + (f" av {team_row['checked_in_by']}" if team_row["checked_in_by"] else ""))
            if c1.button("Ta bort incheckning", key=f"portal_uncheck_{team_id}"):
                run("UPDATE teams SET checked_in=0,checked_in_at=NULL,checked_in_by=NULL WHERE id=?", (team_id,))
                record_audit(tournament_id, "team_checkin", "team", f"{team_row['name']}: incheckning borttagen", entity_id=team_id, actor=role_label)
                st.rerun()
        else:
            checkin_name = c1.text_input("Vem checkar in laget?", placeholder="Namn", key=f"checkin_name_{team_id}")
            if c1.button("✅ Vi är på plats", type="primary", key=f"portal_check_{team_id}", use_container_width=True):
                run(
                    "UPDATE teams SET checked_in=1,checked_in_at=?,checked_in_by=? WHERE id=?",
                    (datetime.now().isoformat(timespec="seconds"), checkin_name.strip() or role_label, team_id),
                )
                record_audit(tournament_id, "team_checkin", "team", f"{team_row['name']}: incheckad", entity_id=team_id, actor=role_label)
                st.rerun()

        if team_row["kit_confirmed_at"]:
            c2.success(f"👕 Matchställ bekräftade {team_row['kit_confirmed_at']}")
        else:
            c2.info("👕 Matchställ är ännu inte bekräftade.")
        c2.markdown(kit_preview_html(_team_value(team_row, "home_pattern", "Helfärgad"), team_row["primary_color"], _team_value(team_row, "home_color_2", "#FFFFFF"), "Hemmaställ"), unsafe_allow_html=True)
        c2.markdown(kit_preview_html(_team_value(team_row, "away_pattern", "Helfärgad"), team_row["secondary_color"], _team_value(team_row, "away_color_2", "#111827"), "Bortaställ"), unsafe_allow_html=True)
        if c2.button("Bekräfta matchställ", key=f"confirm_kit_{team_id}", use_container_width=True):
            run("UPDATE teams SET kit_confirmed_at=? WHERE id=?", (datetime.now().isoformat(timespec="seconds"), team_id))
            record_audit(tournament_id, "kit_confirmed", "team", f"{team_row['name']}: matchställ bekräftade", entity_id=team_id, actor=role_label)
            st.rerun()

        st.subheader("Mina matcher")
        matches = [
            row for row in all_rows(
                "SELECT * FROM matches WHERE tournament_id=? AND scheduled_start IS NOT NULL ORDER BY scheduled_start,pitch_number,id",
                (tournament_id,),
            )
            if team_id in _match_team_ids(row)
        ]
        if matches:
            for match_row in matches:
                score = ""
                if match_row["home_score"] is not None and match_row["away_score"] is not None:
                    score = f" · {match_row['home_score']}–{match_row['away_score']}"
                st.markdown(f"**{html.escape(_portal_match_label(match_row))}{score}**")
        else:
            st.info("Inga schemalagda matcher ännu.")

        st.subheader("Ansvarig kontaktperson")
        with st.form(f"portal_contact_{team_id}"):
            contact_name = st.text_input("Namn", value=_team_value(team_row, "responsible_name", "") or "")
            contact_phone = st.text_input("Telefon", value=_team_value(team_row, "responsible_phone", "") or "")
            contact_email = st.text_input("E-post", value=_team_value(team_row, "responsible_email", "") or "")
            protected_contact = st.checkbox(
                "Skyddade kontaktuppgifter – får inte visas publikt",
                value=bool(_team_value(team_row, "responsible_contact_protected", 1)),
                help="Admin och lagets behöriga användare kan fortfarande se uppgifterna.",
            )
            allow_public = bool(_row_value(tournament, "allow_team_public_contact", 0)) and not protected_contact
            contact_public = st.checkbox(
                "Visa kontaktpersonen publikt",
                value=bool(_team_value(team_row, "public_contact_enabled", 0)) and allow_public,
                disabled=not allow_public,
            )
            if st.form_submit_button("Spara kontaktuppgifter"):
                public_enabled = int(bool(contact_public) and not protected_contact and bool(_row_value(tournament, "allow_team_public_contact", 0)))
                run(
                    """UPDATE teams SET responsible_name=?,responsible_phone=?,responsible_email=?,responsible_contact_protected=?,
                       public_contact_name=?,public_contact_phone=?,public_contact_email=?,public_contact_enabled=? WHERE id=?""",
                    (contact_name.strip(), contact_phone.strip(), contact_email.strip(), int(protected_contact),
                     contact_name.strip(), contact_phone.strip(), contact_email.strip(), public_enabled, team_id),
                )
                st.success("Kontaktuppgifterna är sparade.")
                st.rerun()

    with portal_tabs[1]:
        st.subheader("Hantera truppen")
        max_roster = int(_row_value(tournament, "max_roster_size", 0) or 0)
        players = all_rows("SELECT * FROM players WHERE team_id=? ORDER BY player_number,name", (team_id,))
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
                    run("INSERT INTO players(team_id,player_number,name,first_name,last_name,birth_year,position,is_protected) VALUES(?,?,?,?,?,?,?,?)", (team_id, pnumber, full_name, pfirst.strip(), plast.strip(), int(pbirth), pposition.strip(), int(pprotected)))
                    record_audit(tournament_id, "roster_player_added", "team", f"{team_row['name']}: {full_name} tillagd", entity_id=team_id, actor=role_label)
                    st.rerun()
        for player in players:
            with st.expander(f"#{player['player_number'] if player['player_number'] is not None else '–'} {_player_display_name(player)}"):
                with st.form(f"portal_edit_player_{player['id']}"):
                    ec1, ec2 = st.columns(2)
                    legacy_parts = str(player["name"] or "").strip().split(" ", 1)
                    default_first = _row_value(player, "first_name", "") or (legacy_parts[0] if legacy_parts else "")
                    default_last = _row_value(player, "last_name", "") or (legacy_parts[1] if len(legacy_parts) > 1 else "")
                    efirst = ec1.text_input("Förnamn", value=default_first)
                    elast = ec2.text_input("Efternamn", value=default_last)
                    ec3, ec4, ec5 = st.columns(3)
                    enumber = ec3.number_input("Nummer", 0, 999, int(player["player_number"] or 0))
                    ebirth = ec4.number_input("Födelseår", 1900, datetime.now().year, int(_row_value(player, "birth_year", datetime.now().year - 12) or datetime.now().year - 12))
                    eposition = ec5.text_input("Position/roll", value=player["position"] or "")
                    eprotected = st.checkbox("Skyddad spelare – visa inte namn publikt", value=bool(_row_value(player, "is_protected", 0)))
                    save_player = st.form_submit_button("Spara")
                if save_player:
                    if not efirst.strip() or not elast.strip():
                        st.error("Ange både förnamn och efternamn.")
                    else:
                        full_name = f"{efirst.strip()} {elast.strip()}"
                        run("UPDATE players SET name=?,first_name=?,last_name=?,player_number=?,birth_year=?,position=?,is_protected=? WHERE id=? AND team_id=?", (full_name, efirst.strip(), elast.strip(), enumber, int(ebirth), eposition.strip(), int(eprotected), player["id"], team_id))
                        st.rerun()
                if st.button("Ta bort spelaren", key=f"portal_delete_player_{player['id']}"):
                    run("DELETE FROM players WHERE id=? AND team_id=?", (player["id"], team_id))
                    record_audit(tournament_id, "roster_player_deleted", "team", f"{team_row['name']}: spelare borttagen", entity_id=team_id, actor=role_label)
                    st.rerun()

    with portal_tabs[2]:
        st.subheader("Matchtrupper")
        deadline_minutes = int(_row_value(tournament, "squad_deadline_minutes", 30) or 0)
        st.caption(f"Matchtruppen låses {deadline_minutes} minuter före matchstart. Admin kan alltid ändra den.")
        team_matches = [
            row for row in all_rows(
                "SELECT * FROM matches WHERE tournament_id=? AND scheduled_start IS NOT NULL ORDER BY scheduled_start,id",
                (tournament_id,),
            ) if team_id in _match_team_ids(row)
        ]
        if not team_matches:
            st.info("Inga matcher att registrera matchtrupp för ännu.")
        else:
            match_id = st.selectbox("Välj match", [row["id"] for row in team_matches], format_func=lambda mid: _portal_match_label(next(row for row in team_matches if row["id"] == mid)), key=f"portal_squad_match_{team_id}")
            match_row = next(row for row in team_matches if row["id"] == match_id)
            locked = squad_is_locked(match_row["scheduled_start"], deadline_minutes)
            deadline = squad_deadline_at(match_row["scheduled_start"], deadline_minutes)
            if locked:
                st.warning(f"Matchtruppen är låst. Deadline var {swedish_datetime(deadline.isoformat(timespec='minutes'))}.")
            else:
                st.info(f"Deadline: {swedish_datetime(deadline.isoformat(timespec='minutes')) if deadline else 'Ingen deadline'}")
            players = all_rows("SELECT * FROM players WHERE team_id=? ORDER BY player_number,name", (team_id,))
            existing_ids = {int(row["player_id"]) for row in all_rows("SELECT player_id FROM match_rosters WHERE match_id=? AND team_id=?", (match_id, team_id))}
            options = [int(row["id"]) for row in players]
            selected_ids = st.multiselect(
                "Spelare i matchtruppen",
                options,
                default=[pid for pid in options if pid in existing_ids],
                format_func=lambda pid: next(f"#{row['player_number'] if row['player_number'] is not None else '–'} {row['name']}" for row in players if int(row["id"]) == int(pid)),
                disabled=locked,
                key=f"portal_match_roster_{match_id}_{team_id}",
            )
            prev_with_roster = None
            for candidate in reversed([row for row in team_matches if row["scheduled_start"] < match_row["scheduled_start"]]):
                count = one_row("SELECT COUNT(*) AS n FROM match_rosters WHERE match_id=? AND team_id=?", (candidate["id"], team_id))
                if count and int(count["n"] or 0) > 0:
                    prev_with_roster = candidate
                    break
            bc1, bc2 = st.columns(2)
            if bc1.button("Spara matchtrupp", type="primary", disabled=locked, key=f"save_match_roster_{match_id}_{team_id}", use_container_width=True):
                _save_match_roster(match_id, team_id, selected_ids, role_label)
                record_audit(tournament_id, "match_roster_saved", "match", f"{team_row['name']}: matchtrupp sparad ({len(selected_ids)} spelare)", entity_id=match_id, actor=role_label)
                st.success("Matchtruppen är sparad.")
                st.rerun()
            if bc2.button("Kopiera föregående matchtrupp", disabled=locked or prev_with_roster is None, key=f"copy_match_roster_{match_id}_{team_id}", use_container_width=True):
                previous_ids = [row["player_id"] for row in all_rows("SELECT player_id FROM match_rosters WHERE match_id=? AND team_id=?", (prev_with_roster["id"], team_id))]
                valid_ids = {int(row["id"]) for row in players}
                _save_match_roster(match_id, team_id, [pid for pid in previous_ids if int(pid) in valid_ids], role_label)
                st.success("Föregående matchtrupp kopierades.")
                st.rerun()
            if not existing_ids:
                st.warning("⚠️ Matchtrupp ej registrerad.")

    with portal_tabs[3]:
        st.subheader("Meddelanden för laget")
        notifications = all_rows(
            "SELECT * FROM notifications WHERE tournament_id=? AND (team_id=? OR team_id IS NULL) ORDER BY created_at DESC,id DESC LIMIT 100",
            (tournament_id, team_id),
        )
        if not notifications:
            st.info("Inga meddelanden ännu.")
        for note in notifications:
            st.markdown(f"**{html.escape(note['title'])}**  \n{html.escape(note['message'])}")
            st.caption(note["created_at"])


init_db()


# SIDOMENY OCH TURNERING
st.sidebar.title(f"🏆 {tr('Turneringar')}")
st.sidebar.caption(f"CupNavi version {APP_VERSION}")
language_options = {"sv": "Svenska", "en": "English"}
selected_language = st.sidebar.selectbox(
    "🌐 " + tr("Välj språk"),
    list(language_options),
    index=0 if current_language() == "sv" else 1,
    format_func=lambda code: language_options[code],
    key="language_selector",
)
if st.session_state.get("language") != selected_language:
    st.session_state["language"] = selected_language
    st.rerun()

_install_streamlit_translation_hooks()
st.sidebar.caption("Databas: Turso" if CLOUD_DATABASE_ENABLED else "Databas: Lokal SQLite")
mode_options = (
    ["Turneringsvy", "Lagportal", "Matchrapportör", "Admin"]
    if CLOUD_DATABASE_ENABLED
    else ["Admin", "Lagportal", "Matchrapportör", "Turneringsvy"]
)
if st.session_state.get("view_mode") not in mode_options:
    st.session_state["view_mode"] = mode_options[0]

# Ett gemensamt lägesval med vanliga Streamlit-knappar.
# on_click uppdaterar state före rerun, så markering och admininloggning
# alltid hänger ihop på första klicket.
def _set_view_mode(mode):
    st.session_state["view_mode"] = mode

st.caption(tr("Välj läge"))
mode_col1, mode_col2, mode_col3, mode_col4 = st.columns(4)
current_mode = st.session_state["view_mode"]
mode_col1.button(
    tr("Turneringsvy"),
    key="view_mode_public_button",
    type="primary" if current_mode == "Turneringsvy" else "secondary",
    use_container_width=True,
    on_click=_set_view_mode,
    args=("Turneringsvy",),
)
mode_col2.button(
    "Lagportal",
    key="view_mode_team_portal_button",
    type="primary" if current_mode == "Lagportal" else "secondary",
    use_container_width=True,
    on_click=_set_view_mode,
    args=("Lagportal",),
)
mode_col3.button(
    tr("Matchrapportör"),
    key="view_mode_reporter_button",
    type="primary" if current_mode == "Matchrapportör" else "secondary",
    use_container_width=True,
    on_click=_set_view_mode,
    args=("Matchrapportör",),
)
mode_col4.button(
    tr("Admin"),
    key="view_mode_admin_button",
    type="primary" if current_mode == "Admin" else "secondary",
    use_container_width=True,
    on_click=_set_view_mode,
    args=("Admin",),
)
view_mode = st.session_state["view_mode"]

st.sidebar.caption(f"{tr('Visningsläge')}: {tr(view_mode)}")
if RELEASE_FILES_MISMATCH and view_mode == "Admin":
    st.sidebar.error(
        f"Ofullständig release\n\n"
        f"app.py: {APP_BUILD_VERSION}\n\n"
        f"cupnavi_core/version.py: {CORE_APP_VERSION}\n\n"
        "Lägg in hela releasepaketet i GitHub, inte bara app.py. "
        "Kontrollera särskilt cupnavi_core/version.py. Starta sedan om Streamlit-appen."
    )

if view_mode == "Matchrapportör":
    require_match_reporter_access()

if view_mode == "Admin":
    require_admin_access()
    with st.sidebar.expander("Skapa ny turnering"):
        template_id = st.selectbox(
            "Startmall",
            list(TOURNAMENT_TEMPLATES),
            format_func=lambda key: TOURNAMENT_TEMPLATES[key]["label_sv"],
            key="new_tournament_template",
            help="Mallen sätter bara bra startvärden. Du kan justera övriga regler efter att cupen skapats.",
        )
        selected_template = template_definition(template_id)
        st.caption(selected_template["description_sv"])
        with st.form("new_tournament", clear_on_submit=True):
            n = st.text_input("Namn")
            place = st.text_input("Spelort")
            sports_list = list(SPORT_PROFILES)
            suggested_sport = selected_template["sport"] if selected_template["sport"] in sports_list else sports_list[0]
            sport = st.selectbox(
                "Sport",
                sports_list,
                index=sports_list.index(suggested_sport),
                key="new_tournament_sport",
                help="Sport väljs när cupen skapas och låses därefter, eftersom den styr matchmodell, terminologi och sportregler.",
            )
            st.markdown("##### Internationell grund")
            create_locale = st.selectbox(
                "Språk/region",
                list(SUPPORTED_LOCALES),
                index=list(SUPPORTED_LOCALES).index(DEFAULT_LOCALE) if DEFAULT_LOCALE in SUPPORTED_LOCALES else 0,
                key="new_tournament_locale",
                help="Väljs vid skapandet och används som cupens regionala grundinställning.",
            )
            create_timezone = st.text_input(
                "Tidszon",
                value=DEFAULT_TIMEZONE,
                key="new_tournament_timezone",
                help="IANA-tidszon, exempelvis Europe/Stockholm, Europe/London eller America/New_York. Låses efter skapandet.",
            )
            create_country = st.text_input(
                "Landkod",
                value="SE",
                max_chars=2,
                key="new_tournament_country",
                help="Två bokstäver enligt ISO-format, exempelvis SE, GB eller US. Låses efter skapandet.",
            ).upper().strip()
            start_date = st.date_input("Första cupdag")
            end_date = st.date_input("Sista cupdag", value=start_date)
            expected_teams = st.number_input("Planerat antal lag/deltagare", 2, 500, int(selected_template["expected_participants"]))
            st.caption("Sport, språk/region, tidszon och land är grundegenskaper och kan inte ändras efter att turneringen har skapats. Övriga cupregler kan justeras senare.")
            if st.form_submit_button("Skapa", type="primary", use_container_width=True):
                normalized_timezone = valid_timezone(create_timezone)
                if not n.strip():
                    st.error("Ange ett namn.")
                elif end_date < start_date:
                    st.error("Sista cupdagen får inte ligga före första cupdagen.")
                elif normalized_timezone != create_timezone.strip():
                    st.error("Ogiltig tidszon. Använd ett IANA-namn, exempelvis Europe/Stockholm.")
                elif create_country and (len(create_country) != 2 or not create_country.isalpha()):
                    st.error("Landkod ska vara två bokstäver enligt ISO-format, exempelvis SE, GB eller US.")
                else:
                    participant_type = str(sport_definition(sport)["participant_type"])
                    new_tournament_id = run(
                        """INSERT INTO tournaments(
                               name,location,tournament_date,start_date,end_date,expected_team_count,
                               points_win,points_draw,points_loss,sport,lifecycle_status,
                               locale,timezone_name,participant_type,country_code
                           ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (
                            n.strip(), place.strip(), start_date.isoformat(), start_date.isoformat(), end_date.isoformat(),
                            expected_teams, 3, 1, 0, sport, "draft", create_locale, normalized_timezone,
                            participant_type, create_country or None,
                        ),
                    )
                    used_slugs = [row["public_slug"] for row in all_rows("SELECT public_slug FROM tournaments WHERE public_slug IS NOT NULL")]
                    public_slug = choose_unique_slug(n.strip(), start_date.isoformat(), new_tournament_id, used_slugs)
                    run("UPDATE tournaments SET public_slug=? WHERE id=?", (public_slug, new_tournament_id))
                    defaults = sport_profile(sport)
                    run(
                        """INSERT INTO schedule_rules(
                               tournament_id,halves,minutes_per_half,halftime_minutes,minimum_team_rest_minutes
                           ) VALUES(?,?,?,?,?)
                           ON CONFLICT(tournament_id) DO NOTHING""",
                        (new_tournament_id, defaults["halves"], defaults["minutes_per_half"],
                         defaults["halftime_minutes"], defaults["minimum_team_rest_minutes"]),
                    )
                    add_feed_item(new_tournament_id, f"{n.strip()} skapad", f"Sport: {sport}", category="Cup")
                    st.rerun()

if view_mode == "Admin":
    clone_sources = all_rows(
        "SELECT * FROM tournaments WHERE COALESCE(lifecycle_status,'draft')!='trashed' ORDER BY COALESCE(start_date,tournament_date) DESC,name"
    )
    if clone_sources:
        with st.sidebar.expander("Duplicera tidigare cup"):
            source_id = st.selectbox(
                "Kopiera från",
                [row["id"] for row in clone_sources],
                format_func=lambda value: next(row["name"] for row in clone_sources if row["id"] == value),
                key="clone_source_tournament",
            )
            source = next(row for row in clone_sources if row["id"] == source_id)
            default_clone_name = f"{source['name']} – ny upplaga"
            clone_name = st.text_input("Namn på ny cup", value=default_clone_name, key="clone_tournament_name")
            clone_start = st.date_input("Första cupdag", key="clone_tournament_start")
            clone_end = st.date_input("Sista cupdag", value=clone_start, key="clone_tournament_end")
            copy_teams = st.checkbox("Kopiera deltagare/lag", value=False, key="clone_copy_teams")
            copy_refs = st.checkbox("Kopiera domare", value=False, key="clone_copy_refs")
            st.caption("Schema, resultat, grupper, matchtrupper och historik kopieras aldrig. Den nya cupen skapas alltid som utkast.")
            if st.button("Skapa ny upplaga", key="clone_tournament_button", use_container_width=True):
                if not clone_name.strip():
                    st.error("Ange namn på den nya cupen.")
                elif clone_end < clone_start:
                    st.error("Sista cupdagen får inte ligga före första cupdagen.")
                else:
                    payload = clone_tournament_payload(
                        dict(source),
                        name=clone_name,
                        start_date=clone_start.isoformat(),
                        end_date=clone_end.isoformat(),
                    )
                    clone_columns = list(payload)
                    placeholders = ",".join("?" for _ in clone_columns)
                    new_id = run(
                        f"INSERT INTO tournaments({','.join(clone_columns)}) VALUES({placeholders})",
                        tuple(payload[column] for column in clone_columns),
                    )
                    source_rule = one_row("SELECT * FROM schedule_rules WHERE tournament_id=?", (source_id,))
                    if source_rule:
                        rule_columns = [key for key in dict(source_rule) if key != "tournament_id"]
                        run(
                            f"INSERT INTO schedule_rules(tournament_id,{','.join(rule_columns)}) VALUES(?,{','.join('?' for _ in rule_columns)})",
                            (new_id, *(source_rule[column] for column in rule_columns)),
                        )
                    if copy_teams:
                        source_teams = all_rows("SELECT name,primary_color,secondary_color,home_pattern,home_color_2,away_pattern,away_color_2,distance_km,late_first_match,earliest_first_time,travel_note FROM teams WHERE tournament_id=? ORDER BY id", (source_id,))
                        for row in source_teams:
                            run(
                                """INSERT INTO teams(tournament_id,name,primary_color,secondary_color,home_pattern,home_color_2,away_pattern,away_color_2,distance_km,late_first_match,earliest_first_time,travel_note)
                                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                                (new_id, row["name"], row["primary_color"], row["secondary_color"], row["home_pattern"], row["home_color_2"], row["away_pattern"], row["away_color_2"], row["distance_km"], row["late_first_match"], row["earliest_first_time"], row["travel_note"]),
                            )
                    if copy_refs:
                        for row in all_rows("SELECT name,phone,email,referee_level FROM referees WHERE tournament_id=? ORDER BY id", (source_id,)):
                            run("INSERT INTO referees(tournament_id,name,phone,email,referee_level) VALUES(?,?,?,?,?)", (new_id, row["name"], row["phone"], row["email"], row["referee_level"]))
                    used_slugs = [row["public_slug"] for row in all_rows("SELECT public_slug FROM tournaments WHERE public_slug IS NOT NULL")]
                    slug = choose_unique_slug(clone_name.strip(), clone_start.isoformat(), new_id, used_slugs)
                    run("UPDATE tournaments SET public_slug=? WHERE id=?", (slug, new_id))
                    st.success("Ny upplaga skapad som utkast.")
                    st.rerun()

if view_mode in ("Admin", "Matchrapportör", "Lagportal"):
    tournaments = all_rows(
        "SELECT * FROM tournaments WHERE COALESCE(lifecycle_status,'draft')!='trashed' "
        "ORDER BY CASE COALESCE(lifecycle_status,'draft') WHEN 'live' THEN 0 WHEN 'published' THEN 1 WHEN 'draft' THEN 2 WHEN 'completed' THEN 3 ELSE 4 END, "
        "COALESCE(start_date,tournament_date) DESC,name"
    )
else:
    tournaments = all_rows(
        "SELECT * FROM tournaments WHERE is_published=1 AND COALESCE(lifecycle_status,'published') IN ('published','live','completed') "
        "ORDER BY CASE COALESCE(lifecycle_status,'published') WHEN 'live' THEN 0 WHEN 'published' THEN 1 WHEN 'completed' THEN 2 ELSE 3 END, "
        "COALESCE(start_date,tournament_date) DESC,name"
    )

if not tournaments:
    st.title("🏆 CupNavi")
    st.markdown(
        f"<div class='cup-version-badge'>KÖR VERSION {APP_VERSION}</div>",
        unsafe_allow_html=True,
    )
    if view_mode == "Admin":
        st.info("Skapa den första turneringen i vänstermenyn.")
    elif view_mode == "Matchrapportör":
        st.info("Det finns ingen turnering att rapportera ännu.")
    elif view_mode == "Lagportal":
        st.info("Det finns ingen turnering med registrerade lag ännu.")
    else:
        st.info("Ingen turnering är publicerad ännu.")
    st.stop()

cup_query = st.query_params.get("cup") if hasattr(st, "query_params") else None
requested_cup_id = None
if cup_query:
    cup_query_text = str(cup_query)
    try:
        requested_cup_id = int(cup_query_text)
    except (TypeError, ValueError):
        slug_match = next((row for row in tournaments if row["public_slug"] == cup_query_text), None)
        requested_cup_id = slug_match["id"] if slug_match else None

tournament_ids = [t["id"] for t in tournaments]
default_tournament_index = tournament_ids.index(requested_cup_id) if requested_cup_id in tournament_ids else 0

def _tournament_selector_label(tournament_id):
    row = next(t for t in tournaments if t["id"] == tournament_id)
    status = normalize_status(row["lifecycle_status"], is_published=bool(row["is_published"]))
    label = row["name"]
    if status == "completed":
        year_source = row["start_date"] or row["tournament_date"] or ""
        year = str(year_source)[:4] if year_source else ""
        return f"🏆 {label}{' · ' + year if year else ''} · {status_label(status, current_language())}"
    if status == "live":
        return f"🔴 {label} · {status_label(status, current_language())}"
    return label

tid = st.sidebar.selectbox(
    tr("Aktiv turnering"),
    tournament_ids,
    index=default_tournament_index,
    format_func=_tournament_selector_label,
)
tournament = next(t for t in tournaments if t["id"] == tid)
tournament_lifecycle = normalize_status(tournament["lifecycle_status"], is_published=bool(tournament["is_published"]))

if view_mode == "Lagportal":
    render_team_portal(tid, tournament)
    st.stop()

if view_mode == "Matchrapportör":
    render_match_reporter_view(tid, tournament)
    st.stop()

if view_mode == "Admin":
    st.title(f"🏆 {tournament['name']}")
    admin_status_label = status_label(tournament_lifecycle, current_language())
    schedule_status_label = tr("Schema aktuellt") if not tournament["schedule_dirty"] else tr("Schema behöver uppdateras")
    st.markdown(
        f"<div class='cn-admin-status-strip'>"
        f"<span class='cn-admin-status-pill'>{html.escape(admin_status_label)}</span>"
        f"<span>{html.escape(schedule_status_label)}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div class='cup-version-badge'>KÖR VERSION {APP_VERSION}</div>",
        unsafe_allow_html=True,
    )
    st.caption(f"{tournament['location'] or 'Spelort saknas'} · {cup_date_label(tournament)} · Planerat antal lag: {tournament['expected_team_count'] or 'Ej angivet'}")
    if tournament_lifecycle == "completed":
        st.success("🏆 Cupen är avslutad och ligger kvar som publik historik. Adminläget är skrivskyddat tills cupen återöppnas.")
        st.caption(f"Permanent publik identifierare: {tournament['public_slug'] or tournament['id']}")
        archive_col1, archive_col2 = st.columns(2)
        if archive_col1.button("↩️ Återöppna cup", type="primary", use_container_width=True, key=f"reopen_completed_{tid}"):
            run("UPDATE tournaments SET lifecycle_status='published',completed_at=NULL,is_published=1 WHERE id=?", (tid,))
            st.rerun()
        trash_confirm = archive_col2.checkbox("Tillåt flytt till papperskorg", key=f"archive_trash_confirm_{tid}")
        if archive_col2.button("🗑️ Flytta till papperskorg", disabled=not trash_confirm, use_container_width=True, key=f"archive_trash_{tid}"):
            run("UPDATE tournaments SET lifecycle_status='trashed',trashed_at=?,is_published=0 WHERE id=?", (datetime.now().isoformat(timespec="seconds"), tid))
            st.rerun()
        st.info("Växla till Turneringsvy för att se den arkiverade cupsidan precis som besökarna gör.")
        st.stop()
else:
    st.markdown(
        f"<div class='cup-version-badge'>KÖR VERSION {APP_VERSION}</div>",
        unsafe_allow_html=True,
    )

if view_mode == "Turneringsvy":
    render_public_view(tid, tournament)
    st.stop()

# SNABB ADMINNAVIGERING: visuellt som flikar, men bara vald sida körs.
ADMIN_PAGES = [
    "Instruktioner", "Adminöversikt", "Kontroller", "Lag", "Grupper", "Trupper", "Domare",
    "Skapa och publicera schema", "Tabeller", "Matcher och resultat",
    "Matchhändelser", "Slutspel", "Skytteligor", "Erbjudanden",
    "Sponsorer", "Funktionärer", "Import", "Besöksstatistik", "Cupverktyg",
]
ADMIN_NAV_GROUPS = [
    ("Kom igång", [
        ("Instruktioner", tr("Instruktioner")),
        ("Adminöversikt", tr("Översikt")),
        ("Lag", tr("Lag")),
        ("Grupper", tr("Grupper")),
        ("Trupper", tr("Trupper")),
        ("Import", tr("Import")),
    ]),
    ("Planering", [
        ("Domare", tr("Domare")),
        ("Skapa och publicera schema", tr("Schema")),
        ("Kontroller", tr("Kontroller")),
        ("Slutspel", tr("Slutspel")),
    ]),
    ("Under cupen", [
        ("Matcher och resultat", tr("Matcher")),
        ("Matchhändelser", tr("Händelser")),
        ("Tabeller", tr("Tabeller")),
        ("Skytteligor", tr("Skytteligor")),
        ("Cupverktyg", "Cupverktyg"),
    ]),
    ("Besökare och övrigt", [
        ("Erbjudanden", tr("Erbjudanden")),
        ("Sponsorer", tr("Sponsorer")),
        ("Funktionärer", tr("Funktionärer")),
        ("Besöksstatistik", tr("Besök")),
    ]),
]
ADMIN_NAV = [item for _, items in ADMIN_NAV_GROUPS for item in items]
admin_page_key = f"admin_page_{tid}"
if st.session_state.get(admin_page_key) not in ADMIN_PAGES:
    st.session_state[admin_page_key] = "Adminöversikt"

with st.expander("🔎 Sök i cupen", expanded=False):
    global_query = st.text_input(
        "Sök lag/deltagare, spelare, domare eller matchnummer",
        key=f"global_admin_search_{tid}",
        placeholder="Exempel: ÖSK, Andersson eller 12",
    ).strip()
    if len(global_query) >= 2:
        like_query = f"%{global_query}%"
        search_hits = []
        for row in all_rows("SELECT id,name FROM teams WHERE tournament_id=? AND name LIKE ? ORDER BY name LIMIT 8", (tid, like_query)):
            search_hits.append(("Lag", row["name"], "Lag"))
        for row in all_rows("SELECT players.id,players.name,teams.name AS team_name FROM players JOIN teams ON teams.id=players.team_id WHERE teams.tournament_id=? AND players.name LIKE ? ORDER BY players.name LIMIT 8", (tid, like_query)):
            search_hits.append(("Spelare", f"{row['name']} · {row['team_name']}", "Trupper"))
        for row in all_rows("SELECT id,name FROM referees WHERE tournament_id=? AND name LIKE ? ORDER BY name LIMIT 8", (tid, like_query)):
            search_hits.append(("Domare", row["name"], "Domare"))
        if global_query.isdigit():
            for row in all_rows("SELECT id,match_no,stage FROM matches WHERE tournament_id=? AND match_no=? ORDER BY id LIMIT 8", (tid, int(global_query))):
                search_hits.append(("Match", f"Match {row['match_no']} · {row['stage']}", "Matcher och resultat"))
        if search_hits:
            for hit_index, (kind, label, target_page) in enumerate(search_hits[:15]):
                hit_cols = st.columns([4, 1])
                hit_cols[0].markdown(f"**{html.escape(kind)}:** {html.escape(str(label))}")
                if hit_cols[1].button("Öppna", key=f"global_hit_{tid}_{hit_index}", use_container_width=True):
                    st.session_state[admin_page_key] = target_page
                    st.rerun()
        else:
            st.caption("Inga träffar i den aktiva cupen.")

st.markdown(f"### {tr('Administration')}")
st.caption("Välj administrationsdel. Endast den valda delen laddas, för snabbare webbdrift.")

def _set_admin_page(page):
    st.session_state[admin_page_key] = page

# Grupperad navigation minskar mängden likvärdiga val på samma nivå.
for group_title, nav_items in ADMIN_NAV_GROUPS:
    st.markdown(
        f"<div class='cn-admin-nav-group-title'>{html.escape(tr(group_title))}</div>",
        unsafe_allow_html=True,
    )
    nav_cols = st.columns(min(3, len(nav_items)))
    for nav_index, (page_name, button_label) in enumerate(nav_items):
        nav_col = nav_cols[nav_index % len(nav_cols)]
        nav_col.button(
            button_label,
            key=f"admin_nav_v83_{tid}_{page_name}",
            type="primary" if st.session_state[admin_page_key] == page_name else "secondary",
            use_container_width=True,
            on_click=_set_admin_page,
            args=(page_name,),
        )

admin_page = st.session_state[admin_page_key]
current_page_label = dict(ADMIN_NAV).get(admin_page, admin_page)
st.markdown(
    f"<div class='cn-current-admin-page'>"
    f"<span>{html.escape(tr('Aktuell sida'))}</span>"
    f"<strong>{html.escape(current_page_label)}</strong>"
    f"</div>",
    unsafe_allow_html=True,
)
st.divider()

current_schedule_state = one_row(
    "SELECT schedule_dirty,(SELECT COUNT(*) FROM matches WHERE tournament_id=? AND scheduled_start IS NOT NULL) AS scheduled_n "
    "FROM tournaments WHERE id=?",
    (tid, tid),
)
if current_schedule_state and current_schedule_state["schedule_dirty"] and current_schedule_state["scheduled_n"]:
    st.warning(
        "⚠️ Förutsättningarna för turneringen har ändrats efter att schemat skapades. "
        "Schemat är markerat som inaktuellt och bör regenereras under Schema innan det publiceras på nytt."
    )

# Publicering ska kunna hanteras från samtliga adminflikar.
# Valideringen cachas i sessionen och räknas bara om när något schema-/regelrelaterat ändrats.
sidebar_rules = one_row("SELECT * FROM schedule_rules WHERE tournament_id=?", (tid,))
if sidebar_rules is None:
    run("INSERT INTO schedule_rules(tournament_id) VALUES(?)", (tid,))
    sidebar_rules = one_row("SELECT * FROM schedule_rules WHERE tournament_id=?", (tid,))

sidebar_scheduled = one_row(
    "SELECT COUNT(*) AS n FROM matches WHERE tournament_id=? AND scheduled_start IS NOT NULL",
    (tid,),
)["n"]

validation_cache_key = f"_schedule_validation_{tid}"
if sidebar_scheduled:
    if st.session_state.get("_validation_dirty", True) or validation_cache_key not in st.session_state:
        st.session_state[validation_cache_key] = validate_schedule(tid, tournament, sidebar_rules)
        st.session_state["_validation_dirty"] = False
    sidebar_errors, sidebar_warnings, _sidebar_quality = st.session_state.get(
        validation_cache_key, ([], [], [])
    )
else:
    sidebar_errors, sidebar_warnings, _sidebar_quality = ([], [], [])

st.sidebar.divider()
st.sidebar.subheader("Publicering")
if tournament["is_published"]:
    st.sidebar.success("Publicerad")
else:
    st.sidebar.caption("Turneringsvyn är ett utkast.")


def _is_advisory_schedule_warning(message):
    """Varningar som ska synas men aldrig blockera publicering."""
    lowered = (message or "").lower()
    return any(term in lowered for term in ("färgkrock", "tröjfärg", "färglikhet", "extraställ"))


blocking_sidebar_warnings = [
    warning for warning in sidebar_warnings
    if not _is_advisory_schedule_warning(warning)
]
advisory_sidebar_warnings = [
    warning for warning in sidebar_warnings
    if _is_advisory_schedule_warning(warning)
]

sidebar_warnings_approved = st.sidebar.checkbox(
    "Jag har granskat schemavarningarna",
    disabled=not bool(blocking_sidebar_warnings),
    key=f"sidebar_warning_approval_{tid}",
)

publish_blockers = []
if not tournament["playoff_model_confirmed"]:
    publish_blockers.append("Slutspelsmodell och cupregler måste sparas på Översikt.")
if not sidebar_scheduled:
    publish_blockers.append("Spelschema saknas. Generera schemat under Schema.")
if bool(tournament["schedule_dirty"]) and sidebar_scheduled:
    publish_blockers.append(
        "Schemat är inaktuellt eftersom förutsättningarna har ändrats. Regenerera schemat."
    )
if sidebar_errors:
    publish_blockers.append(
        f"{len(sidebar_errors)} blockerande schemafel måste åtgärdas."
    )
if blocking_sidebar_warnings and not sidebar_warnings_approved:
    publish_blockers.append(
        f"{len(blocking_sidebar_warnings)} schemavarningar måste granskas och godkännas."
    )

sidebar_publish_blocked = bool(publish_blockers)

if sidebar_publish_blocked:
    st.sidebar.error("Kan inte publicera ännu")
    for reason in publish_blockers:
        st.sidebar.markdown(f"• {reason}")

    if sidebar_errors:
        with st.sidebar.expander(f"Visa schemafel ({len(sidebar_errors)})"):
            for index, error in enumerate(sidebar_errors[:10], 1):
                st.markdown(f"**{index}.** {error}")
            if len(sidebar_errors) > 10:
                st.caption(f"Ytterligare {len(sidebar_errors) - 10} fel visas under Kontroller/Schema.")

    if blocking_sidebar_warnings:
        with st.sidebar.expander(f"Visa schemavarningar ({len(blocking_sidebar_warnings)})"):
            for index, warning in enumerate(blocking_sidebar_warnings[:10], 1):
                st.markdown(f"**{index}.** {warning}")
            if len(blocking_sidebar_warnings) > 10:
                st.caption(
                    f"Ytterligare {len(blocking_sidebar_warnings) - 10} varningar visas under Kontroller/Schema."
                )
else:
    st.sidebar.success("✓ Alla publiceringskrav är uppfyllda.")

if advisory_sidebar_warnings:
    with st.sidebar.expander(f"Notiser – blockerar inte ({len(advisory_sidebar_warnings)})"):
        for index, warning in enumerate(advisory_sidebar_warnings[:10], 1):
            st.markdown(f"**{index}.** {warning}")
        st.caption("Dessa notiser stoppar inte publicering.")

if st.sidebar.button(
    "Publicera",
    type="primary",
    use_container_width=True,
    disabled=sidebar_publish_blocked,
    key=f"publish_from_any_admin_page_{tid}",
):
    with db() as con:
        con.execute(
            "UPDATE matches SET schedule_published=1 WHERE tournament_id=? AND scheduled_start IS NOT NULL",
            (tid,),
        )
        con.execute("UPDATE tournaments SET is_published=1,lifecycle_status=CASE WHEN lifecycle_status='live' THEN 'live' ELSE 'published' END WHERE id=?", (tid,))
        con.commit()
    st.rerun()

if st.sidebar.button(
    "Avpublicera",
    use_container_width=True,
    disabled=not tournament["is_published"],
    key=f"unpublish_from_any_admin_page_{tid}",
):
    run("UPDATE tournaments SET is_published=0,lifecycle_status='draft' WHERE id=?", (tid,))
    st.rerun()

# Cupens livscykel: publicerad -> pågår -> avslutad. Avslutad cup blir skrivskyddad
# i admin men ligger kvar publikt tills admin uttryckligen flyttar den till papperskorgen.
if tournament_lifecycle == "published" and tournament["is_published"]:
    if st.sidebar.button("🔴 Markera cupen som pågående", use_container_width=True, key=f"mark_live_{tid}"):
        run("UPDATE tournaments SET lifecycle_status='live' WHERE id=?", (tid,))
        st.rerun()

lifecycle_counts = one_row(
    "SELECT COUNT(*) AS total, SUM(CASE WHEN home_score IS NOT NULL AND away_score IS NOT NULL THEN 1 ELSE 0 END) AS played "
    "FROM matches WHERE tournament_id=? AND scheduled_start IS NOT NULL AND schedule_published=1",
    (tid,),
)
life_total = int(lifecycle_counts["total"] or 0) if lifecycle_counts else 0
life_played = int(lifecycle_counts["played"] or 0) if lifecycle_counts else 0
cup_can_complete = life_total > 0 and life_played == life_total and tournament_lifecycle in ("published", "live")
if tournament_lifecycle in ("published", "live"):
    if not cup_can_complete:
        st.sidebar.caption(f"Avsluta cup: {life_played}/{life_total} publicerade matcher färdigrapporterade.")
    if st.sidebar.button("🏁 Avsluta cup", disabled=not cup_can_complete, use_container_width=True, key=f"complete_cup_{tid}"):
        run(
            "UPDATE tournaments SET lifecycle_status='completed',completed_at=?,is_published=1 WHERE id=?",
            (datetime.now().isoformat(timespec="seconds"), tid),
        )
        add_feed_item(tid, "Cupen är avslutad", "Resultat och statistik finns kvar i CupNavi-historiken.", category="Cup")
        st.rerun()


def _demo_distribute_count(total, players):
    """Fördela ett heltalsantal slumpmässigt över spelare."""
    if total <= 0 or not players:
        return {}
    counts = {player["id"]: 0 for player in players}
    for _ in range(total):
        chosen = random.choice(players)
        counts[chosen["id"]] += 1
    return {player_id: count for player_id, count in counts.items() if count}


def _demo_write_match_stats(match_id, team_id, goals, con):
    """Skapa fiktiva mål/assist/kort för ett lag i en redan resultatsatt match."""
    players = _rows_from_cursor(
        con.execute(
            "SELECT id,name FROM players WHERE team_id=? ORDER BY player_number,name",
            (team_id,),
        )
    )
    if not players:
        return 0

    goal_map = _demo_distribute_count(goals, players)

    # Alla mål behöver inte ha assist. Antalet assist kan aldrig överstiga antalet mål.
    assist_total = random.randint(0, goals) if goals > 0 else 0
    assist_map = _demo_distribute_count(assist_total, players)

    # Kortdata är separat från mål/assist.
    yellow_total = random.choices([0, 1, 2, 3], weights=[45, 35, 15, 5], k=1)[0]
    red_total = random.choices([0, 1], weights=[92, 8], k=1)[0]
    yellow_map = _demo_distribute_count(yellow_total, players)
    red_map = _demo_distribute_count(red_total, players)

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


def _demo_generate_group_results(tournament_id):
    """Slumpa resultat och matchhändelser för alla gruppspelsmatcher."""
    group_matches = all_rows(
        """SELECT * FROM matches
           WHERE tournament_id=? AND stage='Gruppspel'
           ORDER BY COALESCE(scheduled_start,''),group_id,match_no,id""",
        (tournament_id,),
    )
    if not group_matches:
        return 0, 0, "Inga gruppspelsmatcher finns ännu. Generera spelschemat först."

    generated = 0
    stat_rows = 0
    with db() as con:
        for match_row in group_matches:
            home_id = resolve_source(match_row["home_source"])
            away_id = resolve_source(match_row["away_source"])
            if not home_id or not away_id:
                continue

            # Rimliga testresultat med både målsnåla och målglada matcher.
            home_score = random.choices([0,1,2,3,4,5], weights=[14,25,25,19,11,6], k=1)[0]
            away_score = random.choices([0,1,2,3,4,5], weights=[16,27,24,18,10,5], k=1)[0]

            con.execute(
                """UPDATE matches
                   SET home_score=?,away_score=?,home_penalties=NULL,away_penalties=NULL,decided_winner_id=NULL
                   WHERE id=?""",
                (home_score, away_score, match_row["id"]),
            )
            con.execute("DELETE FROM player_match_stats WHERE match_id=?", (match_row["id"],))
            stat_rows += _demo_write_match_stats(match_row["id"], home_id, home_score, con)
            stat_rows += _demo_write_match_stats(match_row["id"], away_id, away_score, con)
            generated += 1
        con.commit()

    _clear_render_query_cache()
    return generated, stat_rows, None


def _demo_generate_playoff_results(tournament_id):
    """Slumpa slutspelsresultat i spelordning så vinnare går vidare till nästa match."""
    playoff_matches = all_rows(
        """SELECT * FROM matches
           WHERE tournament_id=? AND stage<>'Gruppspel'
           ORDER BY round_no,match_no,id""",
        (tournament_id,),
    )
    if not playoff_matches:
        return 0, 0, "Inga slutspelsmatcher finns ännu. Generera spelschemat först."

    tournament_row = one_row("SELECT * FROM tournaments WHERE id=?", (tournament_id,))
    tie_rule = tournament_row["playoff_tie_rule"] or "Straffar direkt"
    generated = 0
    stat_rows = 0
    skipped = 0

    # Kör match för match och commit:a varje resultat så winner:<match-id>
    # kan lösas direkt i efterföljande semifinal/final.
    for match_stub in playoff_matches:
        _clear_render_query_cache()
        match_row = one_row("SELECT * FROM matches WHERE id=?", (match_stub["id"],))
        home_id = resolve_source(match_row["home_source"])
        away_id = resolve_source(match_row["away_source"])
        if not home_id or not away_id:
            skipped += 1
            continue

        # Cirka 25 % av matcherna går till oavgjort i ordinarie tid så
        # straff/lottning också får testdata.
        if random.random() < 0.25:
            score = random.choice([0, 1, 2, 3])
            home_score = away_score = score
        else:
            home_score = random.choices([0,1,2,3,4], weights=[15,28,27,20,10], k=1)[0]
            away_score = random.choices([0,1,2,3,4], weights=[15,28,27,20,10], k=1)[0]
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

        with db() as con:
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
            stat_rows += _demo_write_match_stats(match_row["id"], home_id, home_score, con)
            stat_rows += _demo_write_match_stats(match_row["id"], away_id, away_score, con)
            con.commit()

        _clear_render_query_cache()
        generated += 1

    warning = None
    if skipped:
        warning = (
            f"{skipped} slutspelsmatcher kunde inte fyllas eftersom deltagande lag ännu inte kunde avgöras. "
            "Kontrollera att gruppspelet är färdigspelat och kör sedan knappen igen."
        )
    return generated, stat_rows, warning



def _admin_workflow_counts(tournament_id):
    return one_row(
        """SELECT
          (SELECT COUNT(*) FROM teams WHERE tournament_id=?) AS teams_n,
          (SELECT COUNT(*) FROM groups WHERE tournament_id=?) AS groups_n,
          (SELECT COUNT(*) FROM players p JOIN teams t ON t.id=p.team_id WHERE t.tournament_id=?) AS players_n,
          (SELECT COUNT(*) FROM referees WHERE tournament_id=?) AS refs_n,
          (SELECT COUNT(*) FROM matches WHERE tournament_id=?) AS matches_n,
          (SELECT COUNT(*) FROM matches WHERE tournament_id=? AND home_score IS NOT NULL AND away_score IS NOT NULL) AS played_n
        """,
        (tournament_id, tournament_id, tournament_id, tournament_id, tournament_id, tournament_id),
    )


def _admin_workflow_step(title, state, meta):
    css_class = "done" if state == "done" else ("warn" if state == "warn" else "todo")
    icon = "✓" if state == "done" else ("⚠" if state == "warn" else "○")
    return (
        f"<div class='cn-step {css_class}'>"
        f"<div class='title'>{icon} {html.escape(title)}</div>"
        f"<div class='meta'>{html.escape(meta)}</div>"
        "</div>"
    )



if admin_page == "Instruktioner":
    st.header("Instruktioner")
    st.caption(
        "En steg-för-steg-guide för dig som administrerar en cup för första gången. "
        "Guiden läser av den valda turneringen och ändrar status och nästa rekommenderade steg automatiskt."
    )

    guide_counts = _admin_workflow_counts(tid)
    guide_expected = int(tournament["expected_team_count"] or 0)
    guide_scheduled = one_row(
        "SELECT COUNT(*) AS n FROM matches WHERE tournament_id=? AND scheduled_start IS NOT NULL",
        (tid,),
    )["n"]
    guide_published = one_row(
        "SELECT COUNT(*) AS n FROM matches WHERE tournament_id=? AND schedule_published=1",
        (tid,),
    )["n"]
    guide_events = one_row(
        """SELECT COUNT(*) AS n
           FROM player_match_stats s
           JOIN matches m ON m.id=s.match_id
           WHERE m.tournament_id=?
             AND (s.goals>0 OR s.assists>0 OR s.yellow_cards>0 OR s.red_cards>0)""",
        (tid,),
    )["n"]

    guide_steps = [
        {
            "title": "1. Grundinställningar",
            "page": "Adminöversikt",
            "done": bool(tournament["name"]) and guide_expected > 0,
            "text": (
                "Börja på Översikt. Ange cupens grunduppgifter, maximalt/planerat antal lag, "
                "datum och plantider. Här bestämmer du också tabellregler, slutspelsmodell och "
                "hur oavgjorda slutspelsmatcher ska avgöras."
            ),
        },
        {
            "title": "2. Registrera lag",
            "page": "Lag",
            "done": guide_counts["teams_n"] > 0 and (guide_expected == 0 or guide_counts["teams_n"] >= guide_expected),
            "text": (
                f"Registrera deltagande lag och deras hemma- och bortaställ. "
                f"Just nu finns {guide_counts['teams_n']} lag registrerade"
                + (f" av {guide_expected} planerade." if guide_expected else ".")
            ),
        },
        {
            "title": "3. Skapa grupper",
            "page": "Grupper",
            "done": guide_counts["groups_n"] > 0,
            "text": (
                f"Skapa grupper och placera lagen i rätt grupp. "
                f"Just nu finns {guide_counts['groups_n']} grupper."
            ),
        },
        {
            "title": "4. Lägg in trupper",
            "page": "Trupper",
            "done": guide_counts["players_n"] > 0,
            "text": (
                f"Lägg in spelarna under respektive lag. Trupper behövs för att kunna registrera "
                f"mål, assist och kort på rätt spelare. {guide_counts['players_n']} spelare är registrerade."
            ),
        },
        {
            "title": "5. Registrera domare",
            "page": "Domare",
            "done": guide_counts["refs_n"] > 0,
            "text": (
                f"Lägg in de domare som ska användas. CupNavi kan sedan tilldela dem i schemat. "
                f"{guide_counts['refs_n']} domare är registrerade."
            ),
        },
        {
            "title": "6. Skapa och kontrollera schemat",
            "page": "Skapa och publicera schema",
            "done": guide_scheduled > 0 and not bool(tournament["schedule_dirty"]),
            "text": (
                f"När lag, grupper och regler är klara skapar du schemat. Slutspelsmatcherna skapas "
                f"samtidigt. Kontrollera därefter tider, planer, vila och domare. "
                f"{guide_scheduled} matcher är schemalagda."
                + (" Schemat behöver regenereras efter en ändring." if tournament["schedule_dirty"] and guide_scheduled else "")
            ),
        },
        {
            "title": "7. Kontrollera innan publicering",
            "page": "Kontroller",
            "done": guide_scheduled > 0 and not bool(tournament["schedule_dirty"]),
            "text": (
                "Öppna Kontroller och gå igenom blockerande fel och varningar. Varningar är sådant "
                "du bör granska; blockerande fel måste rättas innan publicering."
            ),
        },
        {
            "title": "8. Publicera cupen",
            "page": "Skapa och publicera schema",
            "done": bool(tournament["is_published"]) and guide_published > 0,
            "text": (
                "När schemat är godkänt publicerar du cupen. Publiceringsfunktionen finns tillgänglig "
                "i adminläget även när du arbetar på andra flikar. Den publika turneringsvyn visar sedan "
                "spelschema, tabeller, resultat, slutspel och övrig information."
            ),
        },
        {
            "title": "9. Under turneringen – registrera resultat",
            "page": "Matcher och resultat",
            "done": guide_counts["played_n"] > 0,
            "text": (
                f"På Matcher registrerar du slutresultaten. De sparas automatiskt när de matas in. "
                f"{guide_counts['played_n']} av {guide_counts['matches_n']} matcher har resultat."
            ),
        },
        {
            "title": "10. Registrera matchhändelser",
            "page": "Matchhändelser",
            "done": guide_events > 0,
            "text": (
                f"På Händelser registrerar du mål, assist, gula kort och röda kort. Händelserna sparas "
                f"automatiskt och används i den publika resultatvyn och topplistorna. "
                f"{guide_events} spelarhändelser finns registrerade."
            ),
        },
        {
            "title": "11. Följ tabeller, slutspel och topplistor",
            "page": "Tabeller",
            "done": guide_counts["played_n"] > 0,
            "text": (
                "Tabeller räknas från registrerade resultat. Slutspelsplatser och kommande motstånd "
                "uppdateras utifrån cupens regler. Kontrollera även Slutspel och Skytteligor under cupens gång."
            ),
        },
        {
            "title": "12. Lägg in erbjudanden för deltagarna",
            "page": "Erbjudanden",
            "done": one_row("SELECT COUNT(*) AS n FROM offers WHERE tournament_id=? AND active=1", (tid,))["n"] > 0,
            "text": (
                "På Erbjudanden kan du lägga upp lokala förmåner för cupdeltagare, till exempel "
                "restaurangrabatter eller rabattkoder. Aktiva erbjudanden visas i en egen flik i turneringsvyn."
            ),
        },
        {
            "title": "13. Importera lag eller trupper vid behov",
            "page": "Import",
            "done": guide_counts["teams_n"] > 0,
            "text": (
                "På Import kan du läsa in många lag eller spelare från CSV/XLSX. "
                "Använd gärna de nedladdningsbara mallarna och kontrollera förhandsgranskningen innan import."
            ),
        },
        {
            "title": "14. Lägg in sponsorer och funktionärer",
            "page": "Sponsorer",
            "done": one_row("SELECT COUNT(*) AS n FROM sponsors WHERE tournament_id=? AND active=1", (tid,))["n"] > 0
                    or one_row("SELECT COUNT(*) AS n FROM functionaries WHERE tournament_id=? AND active=1", (tid,))["n"] > 0,
            "text": (
                "På Sponsorer administrerar du cupens partners. På Funktionärer registrerar du sekretariat, "
                "planvärdar och andra roller. Publika kontakter kan visas i turneringsvyn."
            ),
        },
        {
            "title": "15. Följ besöksstatistiken",
            "page": "Besöksstatistik",
            "done": one_row("SELECT COUNT(*) AS n FROM visitor_sessions WHERE tournament_id=?", (tid,))["n"] > 0,
            "text": (
                "Under Besök ser du hur många som använder den publika cupsidan, sidvisningar över tid, "
                "enheter, webbläsare och trafikkällor. Ingen IP-adress lagras."
            ),
        },
        {
            "title": "16. Exportera scheman",
            "page": "Skapa och publicera schema",
            "done": guide_scheduled > 0,
            "text": (
                "På Schema kan du skapa ett komplett PDF-paket för utskrift. Det innehåller hela schemat "
                "samt separata grupp-, lag-, plan-, slutspels- och domarscheman."
            ),
        },
    ]

    completed_steps = sum(1 for step in guide_steps if step["done"])
    guide_progress = completed_steps / len(guide_steps)
    st.progress(guide_progress, text=f"{completed_steps} av {len(guide_steps)} steg har påbörjats eller slutförts")

    next_step = next((step for step in guide_steps if not step["done"]), None)
    if next_step:
        st.info(f"**Rekommenderat nästa steg:** {next_step['title']} – {next_step['text']}")
        if st.button(
            f"Gå till {next_step['page'].replace('Skapa och publicera schema', 'Schema').replace('Matcher och resultat', 'Matcher').replace('Matchhändelser', 'Händelser')}",
            type="primary",
            key=f"guide_next_{tid}",
        ):
            st.session_state[admin_page_key] = next_step["page"]
            st.rerun()
    else:
        st.success("Grundflödet är genomfört. Fortsätt administrera resultat, händelser och slutspel under cupen.")

    st.markdown("### Så arbetar du i CupNavi")
    for step_index, step in enumerate(guide_steps, start=1):
        icon = "✓" if step["done"] else "○"
        status = "Klart/aktivt" if step["done"] else "Återstår"
        with st.expander(f"{icon} {step['title']} · {status}", expanded=bool(next_step and step["title"] == next_step["title"])):
            st.write(step["text"])
            if st.button(
                f"Öppna {step['page'].replace('Skapa och publicera schema', 'Schema').replace('Matcher och resultat', 'Matcher').replace('Matchhändelser', 'Händelser')}",
                key=f"guide_open_{tid}_{step_index}_{step['page']}",
            ):
                st.session_state[admin_page_key] = step["page"]
                st.rerun()

    st.markdown("### Viktigt att känna till")
    st.markdown(
        """
        - **Ändrar du lag, grupper, regler eller andra schemaförutsättningar efter att schemat skapats** kan schemat markeras som inaktuellt. Regenerera det då på **Schema**.
        - **Färgkrockar är en varning, inte ett stopp.** CupNavi försöker välja hemma/borta och matchställ så att krockarna blir så få som möjligt.
        - **Resultat och matchhändelser sparas automatiskt.** Den gröna bekräftelsen visar att ändringen är sparad.
        - **Publicering valideras innan den genomförs.** Om något blockerar publiceringen ska CupNavi tala om exakt vad som behöver rättas.
        - **Matcher är samlade på en publik sida.** Kommande och spelade matcher visas i samma flöde, med resultat och registrerade händelser när de finns.
        """
    )
    st.caption(
        "Den här sidan bygger sin status från turneringens aktuella data. "
        "När CupNavi får nya arbetssteg eller funktioner ska motsvarande instruktion uppdateras tillsammans med funktionen."
    )


elif admin_page == "Adminöversikt":
    st.header("Adminöversikt")
    current_admin_mode = admin_mode(tournament["start_date"], tournament["end_date"], tournament_lifecycle)
    mode_labels = {
        "planning": "Planeringsläge",
        "live": "🔴 Cupdagsläge",
        "after": "🏆 Efter cupen",
    }
    st.caption(f"Aktuellt arbetsläge: **{mode_labels.get(current_admin_mode, 'Planeringsläge')}**")

    st.markdown("#### Snabbkommandon")
    quick_cols = st.columns(4)
    quick_actions = [
        ("➕ Lag", "Lag"),
        ("🗓️ Schema", "Skapa och publicera schema"),
        ("⚡ Resultat", "Matcher och resultat"),
        ("✅ Kontroller", "Kontroller"),
    ]
    for quick_index, (quick_label, quick_target) in enumerate(quick_actions):
        if quick_cols[quick_index].button(quick_label, key=f"quick_action_{tid}_{quick_index}", use_container_width=True):
            st.session_state[admin_page_key] = quick_target
            st.rerun()

    preview_cols = st.columns(2)
    if preview_cols[0].button("👁️ Förhandsgranska publik vy", key=f"preview_public_{tid}", use_container_width=True):
        st.session_state["view_mode"] = "Turneringsvy"
        if hasattr(st, "query_params"):
            st.query_params["cup"] = tournament["public_slug"] or str(tid)
        st.rerun()
    preview_cols[1].link_button("🔗 Kopiera/öppna publik länk", public_cup_url(tid), use_container_width=True)

    with st.expander("Dela cupen med QR-kod", expanded=False):
        cup_share_url = public_cup_url(tid)
        render_share_panel(tid, tournament["name"])
        render_qr_share_panel(tid, tournament["name"])
        st.code(cup_share_url, language=None)
        qr_bytes = qr_png_bytes(cup_share_url)
        if qr_bytes:
            qr_col1, qr_col2 = st.columns([1, 2])
            qr_col1.image(qr_bytes, width=220)
            qr_col2.download_button(
                "Ladda ner QR-kod",
                data=qr_bytes,
                file_name=f"cupnavi_qr_{tid}.png",
                mime="image/png",
                use_container_width=True,
            )
            qr_col2.caption("Skriv ut QR-koden vid entré, kiosk, sekretariat och planer.")
        else:
            st.warning("QR-biblioteket saknas. Kontrollera att qrcode är installerat från requirements.txt.")
    st.caption("Här ställer du in cupens grunduppgifter, poängregler, slutspelsformat och regler för schemaläggningen.")
    overview_counts = one_row(
        """SELECT
             (SELECT COUNT(*) FROM teams WHERE tournament_id=?) AS teams_n,
             (SELECT COUNT(*) FROM groups WHERE tournament_id=?) AS groups_n,
             (SELECT COUNT(*) FROM matches WHERE tournament_id=?) AS matches_n""",
        (tid, tid, tid),
    )
    overview_team_count = overview_counts["teams_n"]
    overview_group_count = overview_counts["groups_n"]
    overview_match_count = overview_counts["matches_n"]

    workflow_counts = _admin_workflow_counts(tid)
    cup_checklist = checklist_items(
        teams=int(workflow_counts["teams_n"] or 0),
        groups=int(workflow_counts["groups_n"] or 0),
        matches=int(workflow_counts["matches_n"] or 0),
        referees=int(workflow_counts["refs_n"] or 0),
        published=bool(tournament["is_published"]),
        public_contact=bool((tournament["organizer_phone"] or "").strip() or (tournament["feedback_email"] or "").strip()),
    )
    completed_checks = sum(1 for item in cup_checklist if item["done"])
    with st.expander(f"✅ Checklista inför cupstart · {completed_checks}/{len(cup_checklist)}", expanded=current_admin_mode == "live"):
        for check_index, item in enumerate(cup_checklist):
            check_cols = st.columns([5, 1])
            icon = "✅" if item["done"] else "⚠️"
            check_cols[0].markdown(f"{icon} {html.escape(item['label'])}")
            if not item["done"] and check_cols[1].button("Åtgärda", key=f"check_fix_{tid}_{check_index}", use_container_width=True):
                st.session_state[admin_page_key] = item["target"]
                st.rerun()

    expected_teams = int(tournament["expected_team_count"] or 0)
    teams_ready = workflow_counts["teams_n"] > 0 and (
        expected_teams == 0 or workflow_counts["teams_n"] == expected_teams
    )
    groups_ready = workflow_counts["groups_n"] > 0
    players_ready = workflow_counts["players_n"] > 0
    refs_ready = workflow_counts["refs_n"] > 0
    schedule_ready = workflow_counts["matches_n"] > 0 and not bool(tournament["schedule_dirty"])
    results_ready = (
        workflow_counts["matches_n"] > 0
        and workflow_counts["played_n"] == workflow_counts["matches_n"]
    )

    st.markdown(
        f"""
        <div class="cn-dashboard-grid">
          <div class="cn-status-card">
            <div class="cn-label">Lag</div>
            <div class="cn-value">{workflow_counts['teams_n']}</div>
            <div class="cn-sub">Planerat: {expected_teams or 'ej satt'}</div>
          </div>
          <div class="cn-status-card">
            <div class="cn-label">Grupper</div>
            <div class="cn-value">{workflow_counts['groups_n']}</div>
            <div class="cn-sub">Gruppindelning</div>
          </div>
          <div class="cn-status-card">
            <div class="cn-label">Matcher</div>
            <div class="cn-value">{workflow_counts['matches_n']}</div>
            <div class="cn-sub">Spelade: {workflow_counts['played_n']}</div>
          </div>
          <div class="cn-status-card">
            <div class="cn-label">Status</div>
            <div class="cn-value">{'Publicerad' if tournament['is_published'] else 'Utkast'}</div>
            <div class="cn-sub">{'Schema aktuellt' if not tournament['schedule_dirty'] else 'Schema behöver uppdateras'}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    workflow_html = "".join([
        _admin_workflow_step(
            "Lag",
            "done" if teams_ready else "todo",
            f"{workflow_counts['teams_n']} registrerade",
        ),
        _admin_workflow_step(
            "Grupper",
            "done" if groups_ready else "todo",
            f"{workflow_counts['groups_n']} skapade",
        ),
        _admin_workflow_step(
            "Trupper",
            "done" if players_ready else "todo",
            f"{workflow_counts['players_n']} spelare",
        ),
        _admin_workflow_step(
            "Domare",
            "done" if refs_ready else "todo",
            f"{workflow_counts['refs_n']} registrerade",
        ),
        _admin_workflow_step(
            "Schema",
            "done" if schedule_ready else ("warn" if workflow_counts["matches_n"] > 0 else "todo"),
            "Aktuellt" if schedule_ready else (
                "Behöver regenereras" if workflow_counts["matches_n"] > 0 else "Ej genererat"
            ),
        ),
        _admin_workflow_step(
            "Resultat",
            "done" if results_ready else "todo",
            f"{workflow_counts['played_n']} av {workflow_counts['matches_n']} matcher",
        ),
    ])
    st.markdown(f"<div class='cn-workflow'>{workflow_html}</div>", unsafe_allow_html=True)

    # Tydlig rekommendation om nästa arbetssteg.
    if not teams_ready:
        next_step_title = "Nästa steg: registrera lag"
        next_step_target = "Lag"
        next_step_text = "Lägg in samtliga deltagande lag innan gruppindelning."
    elif not groups_ready:
        next_step_title = "Nästa steg: skapa grupper"
        next_step_target = "Grupper"
        next_step_text = "Skapa grupper och placera lagen innan schemat genereras."
    elif not players_ready:
        next_step_title = "Nästa steg: lägg till trupper"
        next_step_target = "Trupper"
        next_step_text = "Trupper behövs för mål, assist och kortstatistik."
    elif not refs_ready:
        next_step_title = "Nästa steg: lägg till domare"
        next_step_target = "Domare"
        next_step_text = "Lägg till domare innan automatisk domartillsättning används."
    elif not workflow_counts["matches_n"]:
        next_step_title = "Nästa steg: generera schema"
        next_step_target = "Skapa och publicera schema"
        next_step_text = "Grunddata är på plats. Generera gruppspel och slutspel."
    elif bool(tournament["schedule_dirty"]):
        next_step_title = "Nästa steg: regenerera schema"
        next_step_target = "Skapa och publicera schema"
        next_step_text = "Förutsättningarna har ändrats sedan schemat skapades."
    elif not results_ready:
        next_step_title = "Nästa steg: registrera resultat"
        next_step_target = "Matcher och resultat"
        next_step_text = "Schemat är klart. Registrera matchresultaten när turneringen spelas."
    else:
        next_step_title = "Nästa steg: granska och publicera"
        next_step_target = "Kontroller"
        next_step_text = "Grundflödet är klart. Kontrollera varningar och publiceringsstatus."

    st.info(f"**{next_step_title}**\\n\\n{next_step_text}")
    if st.button(
        next_step_title,
        key=f"dashboard_next_step_{tid}",
        use_container_width=True,
    ):
        st.session_state[admin_page_key] = next_step_target
        st.rerun()

    if bool(tournament["schedule_dirty"]) and workflow_counts["matches_n"] > 0:
        st.markdown(
            """<div class="cn-action-banner">
            <strong>⚠ Schemat behöver regenereras.</strong><br>
            <span>Något som påverkar schemat har ändrats sedan senaste genereringen.</span>
            </div>""",
            unsafe_allow_html=True,
        )
        if st.button(
            "Gå till Schema",
            type="primary",
            use_container_width=True,
            key=f"dashboard_go_schedule_{tid}",
        ):
            st.session_state[admin_page_key] = "Skapa och publicera schema"
            st.rerun()
    st.subheader("Cupens grunduppgifter")
    saved_start = datetime.fromisoformat(tournament["start_date"] or tournament["tournament_date"]).date()
    saved_end = datetime.fromisoformat(tournament["end_date"] or tournament["start_date"] or tournament["tournament_date"]).date()
    overview_rules = one_row("SELECT * FROM schedule_rules WHERE tournament_id=?", (tid,))
    if overview_rules is None:
        run("INSERT INTO schedule_rules(tournament_id) VALUES(?)", (tid,))
        overview_rules = one_row("SELECT * FROM schedule_rules WHERE tournament_id=?", (tid,))
    placement_format = PLACEMENT_PLAYOFF_FORMAT
    format_options = ["Inget slutspel", "A- och B-slutspel", placement_format]
    stored_format = placement_format if tournament["playoff_format"] == "Flera egna slutspel" else tournament["playoff_format"]
    saved_format = stored_format if stored_format in format_options else "Inget slutspel"
    if not tournament["playoff_model_confirmed"]:
        st.warning("Välj och spara slutspelsmodell innan spelschemat kan genereras.")
    current_team_count_for_limit = one_row("SELECT COUNT(*) AS n FROM teams WHERE tournament_id=?", (tid,))["n"]

    st.markdown("#### Sportprofil och internationell grund")
    saved_sport = _row_value(tournament, "sport", "Fotboll")
    selected_profile = sport_profile(saved_sport)
    selected_match_format = match_format(saved_sport)
    saved_locale = _row_value(tournament, "locale", DEFAULT_LOCALE)
    saved_timezone = _row_value(tournament, "timezone_name", DEFAULT_TIMEZONE)
    saved_country = _row_value(tournament, "country_code", "") or "Ej angivet"
    participant_type = _row_value(tournament, "participant_type", str(sport_definition(saved_sport)["participant_type"]))
    st.info(
        f"**{saved_sport}** · {saved_locale} · {saved_timezone} · {saved_country}  \n"
        "Dessa grundinställningar valdes när turneringen skapades och är låsta för att skydda matchmodell, statistik och regional tolkning."
    )
    st.caption(
        f"Sportstandard: {selected_profile['halves']} {selected_profile['period_label']} × "
        f"{selected_profile['minutes_per_half']} min · vila {selected_profile['minimum_team_rest_minutes']} min · "
        f"resultatmodell: {selected_match_format.scoring_mode} · segmenttyp: {selected_match_format.segment_kind} · "
        f"intern deltagartyp: {participant_type}."
    )
    st.caption(
        "Schemaläggning: OR-Tools CP-SAT används automatiskt när biblioteket är tillgängligt; "
        "annars används CupNavis säkra heuristiska fallback."
    )
    if st.button("Återställ sportens standardregler", key=f"apply_sport_defaults_{tid}", use_container_width=True):
        before_rules = dict(overview_rules)
        run(
            """UPDATE schedule_rules SET halves=?,minutes_per_half=?,halftime_minutes=?,minimum_team_rest_minutes=?
               WHERE tournament_id=?""",
            (selected_profile["halves"], selected_profile["minutes_per_half"], selected_profile["halftime_minutes"],
             selected_profile["minimum_team_rest_minutes"], tid),
        )
        run("UPDATE tournaments SET schedule_dirty=1,is_published=0 WHERE id=?", (tid,))
        run("UPDATE matches SET schedule_published=0 WHERE tournament_id=?", (tid,))
        record_audit(tid, "sport_defaults", "schedule_rules", f"Standardregler för {saved_sport} tillämpades",
                     entity_id=tid, before=before_rules, after=dict(selected_profile), reversible=False)
        st.session_state["overview_saved_message"] = "Sportprofilens standardregler har lagts in. Schemat behöver regenereras."
        st.rerun()

    # Slutspelsvalen ligger utanför formuläret så de reagerar direkt på användarens val.
    # Streamlit-formulär skickar annars inte widgetändringar förrän "Spara" trycks.
    st.markdown("#### Slutspelsmodell och avgörande")
    playoff_col1, playoff_col2 = st.columns(2)
    edited_format = playoff_col1.selectbox(
        "Typ av slutspel",
        format_options,
        index=format_options.index(saved_format),
        key=f"overview_playoff_format_{tid}",
    )
    edited_bronze = playoff_col2.checkbox(
        "Skapa bronsmatch automatiskt när slutspelsträdet har minst fyra lag",
        value=bool(tournament["bronze_match"]),
        disabled=edited_format == "Inget slutspel",
        key=f"overview_bronze_{tid}",
    )

    st.markdown("##### Oavgjort i slutspelsmatch")
    tie1, tie2 = st.columns(2)
    tie_options = ["Förlängning + straffar", "Straffar direkt", "Lottning"]
    saved_tie_rule = tournament["playoff_tie_rule"] or "Straffar direkt"
    edited_tie_rule = tie1.selectbox(
        "Så avgörs slutspelsmatchen",
        tie_options,
        index=tie_options.index(saved_tie_rule) if saved_tie_rule in tie_options else 1,
        disabled=edited_format == "Inget slutspel",
        key=f"overview_tie_rule_{tid}",
    )
    edited_extra_time = tie2.number_input(
        "Förlängning (minuter)",
        min_value=1,
        max_value=60,
        value=max(1, int(tournament["extra_time_minutes"] or 10)),
        disabled=edited_format == "Inget slutspel" or edited_tie_rule != "Förlängning + straffar",
        help=(
            "Aktiveras när 'Förlängning + straffar' väljs. "
            "Tiden reserveras även i schemaläggningen för slutspelsmatcher."
        ),
        key=f"overview_extra_time_{tid}",
    )
    if edited_format != "Inget slutspel":
        st.success("Slutspelsreglerna är aktiva. Du kan justera dem direkt innan du sparar.")
    else:
        st.caption("Välj en slutspelsmodell för att aktivera reglerna för oavgjorda slutspelsmatcher.")

    with st.form("edit_tournament_basics"):
        st.markdown("#### Cup och deltagande")
        bn1, bn2 = st.columns(2)
        edited_name = bn1.text_input("Turneringens namn", value=tournament["name"])
        edited_location = bn2.text_input("Spelort", value=tournament["location"] or "")
        bc1, bc2, bc3 = st.columns(3)
        edited_start = bc1.date_input("Första cupdag", value=saved_start)
        edited_end = bc2.date_input("Sista cupdag", value=saved_end)
        edited_expected = bc3.number_input("Planerat antal lag", max(2, int(current_team_count_for_limit)), 500, max(int(tournament["expected_team_count"] or 8), int(current_team_count_for_limit)), help="Maxantalet kan inte sättas lägre än antalet lag som redan är registrerade.")

        st.markdown("#### Arena och information till besökare")
        edited_address = st.text_input(
            "Arenaadress", value=tournament["arena_address"] or "",
            placeholder="Exempel: Idrottsvägen 1, 702 00 Örebro",
        )
        edited_kiosk_info = st.text_input(
            "Kiosk och servering (frivillig information)", value=tournament["kiosk_information"] or "",
            placeholder="Exempel: Kiosk finns och är öppen 08.00–17.00 med kaffe, korv och enklare lunch",
        )
        edited_public_info = st.text_area(
            "Egen information på publika infosidan",
            value=tournament["public_information"] or "",
            placeholder="Exempel: Parkering finns vid skolan. Omklädningsrum öppnar 07.30. Hundar ska hållas kopplade.",
            help="Visas under Info efter de automatiskt skapade cupreglerna.",
        )
        contact_col1, contact_col2 = st.columns(2)
        edited_organizer_phone = contact_col1.text_input(
            "Arrangörens telefonnummer",
            value=tournament["organizer_phone"] or "",
            placeholder="Exempel: 070-123 45 67",
            help="Visas publikt som en klickbar ring-knapp under Information.",
        )
        edited_feedback_email = contact_col2.text_input(
            "E-post för feedback",
            value=tournament["feedback_email"] or "",
            placeholder="Exempel: cup@foreningen.se",
            help="Visas publikt som en klickbar e-postknapp för frågor och feedback.",
        )
        edited_instagram = st.text_input(
            "Instagram för cupen",
            value=tournament["instagram_url"] or "",
            placeholder="Exempel: @cupnavi eller https://www.instagram.com/cupnavi/",
            help="Ange användarnamn eller länk. Visas publikt som en knapp för att följa cupen.",
        )

        st.markdown("#### Poängregler och tabell")
        bp1, bp2, bp3 = st.columns(3)
        edited_win = bp1.number_input("Poäng för vinst", 0, 10, int(tournament["points_win"]))
        edited_draw = bp2.number_input("Poäng för oavgjort", 0, 10, int(tournament["points_draw"]))
        edited_loss = bp3.number_input("Poäng för förlust", 0, 10, int(tournament["points_loss"]))

        table_tiebreak_options = ["Målskillnad först", "Inbördes möten först"]
        saved_tiebreak = tournament["table_tiebreak"] or "Målskillnad först"
        edited_tiebreak = st.selectbox(
            "Vid lika poäng avgör i första hand",
            table_tiebreak_options,
            index=table_tiebreak_options.index(saved_tiebreak) if saved_tiebreak in table_tiebreak_options else 0,
        )

        st.markdown("#### Match- och schemaregler")
        br1, br2, br3 = st.columns(3)
        edited_first_time = br1.time_input("Första avspark", value=datetime.strptime(overview_rules["first_match_time"], "%H:%M").time())
        edited_halves = br2.number_input("Antal perioder/halvlekar/set", 1, 4, int(overview_rules["halves"]))
        edited_minutes_half = br3.number_input("Minuter per period/halvlek/set", 1, 120, int(overview_rules["minutes_per_half"]))
        br4, br5 = st.columns(2)
        edited_halftime = br4.number_input("Paus mellan perioder/halvlekar (minuter)", 0, 60, int(overview_rules["halftime_minutes"]))
        edited_pitch_break = br5.number_input("Paus mellan matcher på samma plan", 0, 120, int(overview_rules["pitch_break_minutes"]))
        st.markdown("##### Följdmatcher för samma lag")
        with st.container(border=True):
            follow1, follow2 = st.columns(2)
            edited_avoid_consecutive = follow1.checkbox(
                "Försök undvika matcher direkt efter varandra för samma lag",
                value=bool(overview_rules["avoid_consecutive_matches"]),
            )
            edited_consecutive_break = follow2.number_input(
                "Extra paus om följdmatcher inte kan undvikas (minuter)",
                0, 180, int(overview_rules["consecutive_match_break_minutes"]),
                disabled=not edited_avoid_consecutive,
            )
        br7, br8, br9 = st.columns(3)
        edited_pitch_count = br7.number_input("Antal planer", 1, 30, int(overview_rules["pitch_count"]))
        final_date_label = f"{SWEDISH_WEEKDAYS[edited_end.weekday()]} {edited_end.day} {SWEDISH_MONTHS[edited_end.month - 1]} {edited_end.year}"
        edited_latest = br8.time_input(
            f"Sista plantid – {final_date_label}",
            value=datetime.strptime(overview_rules["latest_kickoff_time"], "%H:%M").time(),
            help="Ingen match får planeras så att den slutar efter denna tid. På sista cupdagen är detta turneringens absoluta sluttid.",
        )
        edited_referee_mode = br9.selectbox("Domartillsättning", ["Automatisk", "Manuell"], index=0 if overview_rules["referee_mode"] == "Automatisk" else 1)
        edited_match_minutes = (edited_halves * edited_minutes_half) + ((edited_halves - 1) * edited_halftime)
        st.info(f"Med dessa regler tar en match {edited_match_minutes} minuter från avspark till slutsignal.")

        if st.form_submit_button("Spara alla grunduppgifter", type="primary", use_container_width=True):
            if not edited_name.strip():
                st.error("Turneringens namn får inte vara tomt.")
            elif edited_end < edited_start:
                st.error("Sista cupdagen får inte ligga före första cupdagen.")
            else:
                scheduling_changed = any([
                    edited_start != saved_start,
                    edited_end != saved_end,
                    edited_first_time.strftime("%H:%M") != overview_rules["first_match_time"],
                    edited_halves != overview_rules["halves"],
                    edited_minutes_half != overview_rules["minutes_per_half"],
                    edited_halftime != overview_rules["halftime_minutes"],
                    edited_pitch_break != overview_rules["pitch_break_minutes"],
                    int(edited_avoid_consecutive) != overview_rules["avoid_consecutive_matches"],
                    edited_consecutive_break != overview_rules["consecutive_match_break_minutes"],
                    edited_pitch_count != overview_rules["pitch_count"],
                    edited_latest.strftime("%H:%M") != overview_rules["latest_kickoff_time"],
                    edited_referee_mode != overview_rules["referee_mode"],
                    edited_format != saved_format,
                    int(edited_bronze) != int(tournament["bronze_match"]),
                    edited_tie_rule != (tournament["playoff_tie_rule"] or "Straffar direkt"),
                    (edited_extra_time if edited_tie_rule == "Förlängning + straffar" else 0) != int(tournament["extra_time_minutes"] or 0),
                ])
                with db() as con:
                    con.execute(
                        """UPDATE tournaments SET name=?,location=?,tournament_date=?,start_date=?,end_date=?,expected_team_count=?,
                        points_win=?,points_draw=?,points_loss=?,playoff_format=?,bronze_match=?,arena_address=?,kiosk_available=?,
                        kiosk_information=?,public_information=?,organizer_phone=?,feedback_email=?,instagram_url=?,table_tiebreak=?,playoff_tie_rule=?,extra_time_minutes=?,playoff_model_confirmed=1
                        WHERE id=?""",
                        (edited_name.strip(), edited_location.strip(), edited_start.isoformat(), edited_start.isoformat(), edited_end.isoformat(),
                         edited_expected, edited_win, edited_draw, edited_loss, edited_format, int(edited_bronze), edited_address.strip(),
                         int(bool(edited_kiosk_info.strip())), edited_kiosk_info.strip(), edited_public_info.strip(),
                         edited_organizer_phone.strip(), edited_feedback_email.strip(), edited_instagram.strip(), edited_tiebreak,
                         edited_tie_rule if edited_format != "Inget slutspel" else "Straffar direkt",
                         edited_extra_time if edited_format != "Inget slutspel" and edited_tie_rule == "Förlängning + straffar" else 0,
                         tid),
                    )
                    con.execute(
                        """UPDATE schedule_rules SET first_match_time=?,halves=?,minutes_per_half=?,halftime_minutes=?,pitch_break_minutes=?,
                        avoid_consecutive_matches=?,consecutive_match_break_minutes=?,pitch_count=?,latest_kickoff_time=?,referee_mode=? WHERE tournament_id=?""",
                        (edited_first_time.strftime("%H:%M"), edited_halves, edited_minutes_half, edited_halftime, edited_pitch_break,
                         int(edited_avoid_consecutive), edited_consecutive_break, edited_pitch_count,
                         edited_latest.strftime("%H:%M"), edited_referee_mode, tid),
                    )
                    if scheduling_changed:
                        con.execute("UPDATE matches SET schedule_published=0 WHERE tournament_id=?", (tid,))
                        con.execute("UPDATE tournaments SET is_published=0,schedule_dirty=1 WHERE id=?", (tid,))
                    con.commit()
                st.session_state["overview_saved_message"] = (
                    "Grunduppgifterna sparades. Ändringarna påverkar schemat, som nu är markerat för regenerering."
                    if scheduling_changed else "Grunduppgifterna sparades."
                )
                st.rerun()
    if "overview_saved_message" in st.session_state:
        st.success(st.session_state.pop("overview_saved_message"))
    if tournament["playoff_format"] != "Inget slutspel":
        st.caption("Typen av slutspel väljs här. Vilka placeringar som möts och hur trädet byggs ställs in under fliken Slutspel.")
    admin_groups = all_rows("SELECT * FROM groups WHERE tournament_id=?", (tid,))
    admin_teams = all_rows("SELECT * FROM teams WHERE tournament_id=?", (tid,))
    admin_matches = all_rows("SELECT * FROM matches WHERE tournament_id=?", (tid,))
    unassigned_teams = [t for t in admin_teams if t["group_id"] is None]
    unscheduled_matches = [m for m in admin_matches if m["scheduled_start"] is None]
    matches_without_referee = [m for m in admin_matches if m["scheduled_start"] is not None and m["referee_id"] is None]
    unpublished_matches = [m for m in admin_matches if m["scheduled_start"] is not None and not m["schedule_published"]]
    scheduled_admin_matches = [m for m in admin_matches if m["scheduled_start"] is not None]
    published_admin_matches = [m for m in scheduled_admin_matches if m["schedule_published"]]
    overview_schedule_errors, overview_schedule_warnings, _ = validate_schedule(tid, tournament, overview_rules)
    st.subheader("Kontroll före turneringsstart")
    checks = [
        (bool(admin_groups), "Minst en grupp är skapad"),
        (bool(admin_teams), "Minst ett lag är registrerat"),
        (len(admin_teams) == int(tournament["expected_team_count"] or 0), f"Registrerade lag stämmer med planerat antal ({len(admin_teams)}/{tournament['expected_team_count'] or 0})"),
        (not unassigned_teams, "Alla lag är placerade i en grupp"),
        (bool(admin_matches), "Matcher är skapade"),
        (not unscheduled_matches, "Alla matcher som kan planeras har en schematid"),
        (not matches_without_referee, "Alla schemalagda matcher har domare"),
        (not unpublished_matches, "Det aktuella schemat är godkänt och publicerat"),
    ]
    for passed, label in checks:
        st.write(f"{'✅' if passed else '⚠️'} {label}")
    st.subheader("Publicering")
    if tournament["is_published"]:
        st.success("Turneringsvyn är publicerad.")
    else:
        st.warning("Turneringsvyn är ett utkast och kan inte ses publikt ännu.")
    ps1, ps2, ps3 = st.columns(3)
    ps1.metric("Schemalagda", len(scheduled_admin_matches))
    ps2.metric("Publicerade", len(published_admin_matches))
    ps3.metric("Kvar i utkast", len(unpublished_matches))
    if not scheduled_admin_matches:
        st.warning("Turneringsvyn kan inte publiceras ännu. Skapa och generera först matcherna under Skapa och publicera schema.")
    elif overview_schedule_errors:
        st.error(f"Schemat har {len(overview_schedule_errors)} blockerande fel. Åtgärda dem på schemafliken före publicering.")
    elif overview_schedule_warnings:
        st.warning(f"Schemat har {len(overview_schedule_warnings)} varningar som måste granskas före publicering.")
    st.info("Publicera eller avpublicera turneringen med knapparna i vänsterspalten. Den publika sidan nås via Visningsläge → Turneringsvy.")

    st.divider()
    st.subheader("⚠️ Riskzon – Cup och papperskorg")
    st.warning(
        "Flytta i första hand en cup till papperskorgen. Då försvinner den från publik vy men all data finns kvar tills admin väljer permanent radering."
    )
    active_delete_tournaments = all_rows(
        "SELECT id,name FROM tournaments WHERE COALESCE(lifecycle_status,'draft')!='trashed' ORDER BY name"
    )
    active_delete_ids = [row["id"] for row in active_delete_tournaments]
    active_delete_name_by_id = {row["id"]: row["name"] for row in active_delete_tournaments}
    if active_delete_ids:
        default_delete_index = active_delete_ids.index(tid) if tid in active_delete_ids else 0
        with st.container(border=True):
            trash_target_id = st.selectbox(
                "Välj cup att flytta till papperskorgen",
                active_delete_ids,
                index=default_delete_index,
                format_func=lambda tournament_id: active_delete_name_by_id[tournament_id],
                key="trash_tournament_target",
            )
            trash_target_name = active_delete_name_by_id[trash_target_id]
            trash_selected = st.checkbox(
                f"Jag vill flytta {trash_target_name} till papperskorgen",
                key=f"trash_tournament_selected_{trash_target_id}",
            )
            if st.button(
                "🗑️ Flytta vald cup till papperskorgen",
                disabled=not trash_selected,
                key=f"trash_tournament_button_{trash_target_id}",
                use_container_width=True,
            ):
                run(
                    "UPDATE tournaments SET lifecycle_status='trashed',trashed_at=?,is_published=0 WHERE id=?",
                    (datetime.now().isoformat(timespec="seconds"), trash_target_id),
                )
                _clear_render_query_cache()
                st.rerun()

    trashed_tournaments = all_rows(
        "SELECT id,name,trashed_at FROM tournaments WHERE lifecycle_status='trashed' ORDER BY trashed_at DESC,name"
    )
    with st.expander(f"Papperskorg ({len(trashed_tournaments)})", expanded=bool(trashed_tournaments)):
        if not trashed_tournaments:
            st.caption("Papperskorgen är tom.")
        else:
            trashed_ids = [row["id"] for row in trashed_tournaments]
            trash_name_by_id = {row["id"]: row["name"] for row in trashed_tournaments}
            trash_row_by_id = {row["id"]: row for row in trashed_tournaments}
            bin_id = st.selectbox(
                "Cup i papperskorgen",
                trashed_ids,
                format_func=lambda tournament_id: trash_name_by_id[tournament_id],
                key="trashed_tournament_target",
            )
            bin_name = trash_name_by_id[bin_id]
            trashed_at = trash_row_by_id[bin_id]["trashed_at"] or "Tid saknas"
            st.caption(f"Flyttad till papperskorgen: {trashed_at.replace('T',' ')}")
            restore_col, permanent_col = st.columns(2)
            if restore_col.button("↩️ Återställ cup", use_container_width=True, key=f"restore_trashed_{bin_id}"):
                run(
                    "UPDATE tournaments SET lifecycle_status='draft',trashed_at=NULL,is_published=0 WHERE id=?",
                    (bin_id,),
                )
                _clear_render_query_cache()
                st.rerun()
            permanent_col.error("Permanent radering går inte att ångra.")
            typed_name = permanent_col.text_input(
                f"Skriv exakt: {bin_name}",
                key=f"permanent_delete_name_{bin_id}",
            )
            if permanent_col.button(
                "Radera permanent",
                disabled=typed_name != bin_name,
                type="primary",
                use_container_width=True,
                key=f"permanent_delete_{bin_id}",
            ):
                with db() as con:
                    con.execute("DELETE FROM tournaments WHERE id=?", (bin_id,))
                    con.commit()
                st.session_state.pop(f"admin_page_{bin_id}", None)
                st.session_state.pop(f"_schedule_validation_{bin_id}", None)
                _clear_render_query_cache()
                st.rerun()


    st.divider()
    st.subheader("Testverktyg")
    st.caption("Använd detta när en extern testare vill prova arbetsflödet utan att först mata in åtta lag manuellt.")
    demo_counts = one_row(
        """SELECT
             (SELECT COUNT(*) FROM teams WHERE tournament_id=?) AS teams_n,
             (SELECT COUNT(*) FROM groups WHERE tournament_id=?) AS groups_n,
             (SELECT COUNT(*) FROM matches WHERE tournament_id=?) AS matches_n""",
        (tid, tid, tid),
    )
    demo_allowed = demo_counts["teams_n"] == 0 and demo_counts["groups_n"] == 0 and demo_counts["matches_n"] == 0
    if not demo_allowed:
        st.caption("Demodata kan bara skapas i en tom turnering, så befintlig cupdata kan aldrig skrivas över.")
    if st.button("Skapa demodata: 8 lag + trupper + 2 grupper", disabled=not demo_allowed, key=f"demo_{tid}"):
        con = db()
        try:
            # Riktiga klubbnamn används som testlag. Alla spelare nedan är påhittad demo-data.
            # Varje körning väljer 3 Allsvenskan + 2 Superettan + 3 Premier League.
            demo_clubs = {
                "Allsvenskan": [
                    ("AIK", "#111111", "#FDE047"), ("BK Häcken", "#FACC15", "#111111"),
                    ("Djurgårdens IF", "#60A5FA", "#1E3A8A"), ("Hammarby IF", "#16A34A", "#FFFFFF"),
                    ("IF Elfsborg", "#FACC15", "#111111"), ("IFK Göteborg", "#2563EB", "#FFFFFF"),
                    ("IFK Norrköping", "#2563EB", "#FFFFFF"), ("Malmö FF", "#7DD3FC", "#FFFFFF"),
                    ("Mjällby AIF", "#FACC15", "#111111"), ("IK Sirius", "#2563EB", "#111111"),
                ],
                "Superettan": [
                    ("Örebro SK", "#111111", "#FFFFFF"), ("Helsingborgs IF", "#DC2626", "#2563EB"),
                    ("Kalmar FF", "#DC2626", "#FFFFFF"), ("Landskrona BoIS", "#111111", "#FFFFFF"),
                    ("GIF Sundsvall", "#2563EB", "#FFFFFF"), ("Örgryte IS", "#DC2626", "#2563EB"),
                    ("IK Brage", "#16A34A", "#FFFFFF"), ("Trelleborgs FF", "#2563EB", "#FFFFFF"),
                ],
                "Premier League": [
                    ("Arsenal", "#DC2626", "#FFFFFF"), ("Aston Villa", "#7F1D1D", "#93C5FD"),
                    ("Chelsea", "#1D4ED8", "#FFFFFF"), ("Liverpool", "#DC2626", "#FFFFFF"),
                    ("Manchester City", "#7DD3FC", "#FFFFFF"), ("Manchester United", "#DC2626", "#111111"),
                    ("Newcastle United", "#111111", "#FFFFFF"), ("Tottenham Hotspur", "#FFFFFF", "#172554"),
                    ("West Ham United", "#7F1D1D", "#93C5FD"),
                ],
            }
            chosen = (
                [("Allsvenskan", *club) for club in random.sample(demo_clubs["Allsvenskan"], 3)]
                + [("Superettan", *club) for club in random.sample(demo_clubs["Superettan"], 2)]
                + [("Premier League", *club) for club in random.sample(demo_clubs["Premier League"], 3)]
            )
            random.shuffle(chosen)

            # Fiktiva namn inspirerade av kända fotbollsstjärnors förnamn/klang,
            # men kombinerade med andra efternamn så de inte påstår sig vara riktiga spelare.
            star_first_names = [
                "Lionel", "Cristiano", "Kylian", "Erling", "Jude", "Mohamed", "Kevin", "Harry",
                "Virgil", "Bukayo", "Cole", "Bruno", "Luka", "Pedri", "Vinícius", "Rodri",
                "Sonny", "Declan", "Phil", "Antoine", "Zlatan", "Alexander", "Martin", "Victor",
            ]
            fun_surnames = [
                "Svensson", "Bergström", "Karlsson", "Lind", "Holm", "Andersson", "Ekström",
                "Nyström", "Dahl", "Sandberg", "Rosén", "Strand", "Björk", "Lund", "Forsberg",
                "Westin", "Hedlund", "Norén", "Engström", "Vik", "Stjärna", "Bollström",
            ]
            patterns = ["Helfärgad", "Vertikala ränder", "Horisontella ränder", "Rutigt", "Delad"]
            away_palette = ["#FFFFFF", "#111827", "#FACC15", "#22C55E", "#F97316", "#E5E7EB", "#7DD3FC"]

            con.execute("UPDATE tournaments SET expected_team_count=8 WHERE id=?", (tid,))
            g1 = con.execute("INSERT INTO groups(tournament_id,name) VALUES(?,?)", (tid, "Grupp A")).lastrowid
            g2 = con.execute("INSERT INTO groups(tournament_id,name) VALUES(?,?)", (tid, "Grupp B")).lastrowid

            # Första passet: skapa alla lag.
            team_specs = []
            for index, (league, club_name, home1, home2) in enumerate(chosen):
                group_id = g1 if index < 4 else g2
                home_pattern = random.choice(patterns)
                away_pattern = random.choice(patterns)
                away1 = random.choice(away_palette)
                away2 = random.choice([color for color in away_palette if color != away1])
                distance = random.choice([0, 12, 25, 48, 75, 110, 165, 220])
                late = 1 if distance >= 110 and random.random() < 0.7 else 0
                earliest = random.choice(["10:00", "10:30", "11:00"]) if late else None
                note = f"Demodata · {league}" + (" · lång resväg" if late else "")
                con.execute(
                    """INSERT INTO teams(
                        tournament_id,name,primary_color,secondary_color,home_pattern,home_color_2,
                        away_pattern,away_color_2,group_id,distance_km,late_first_match,
                        earliest_first_time,travel_note
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (tid, club_name, home1, away1, home_pattern, home2, away_pattern, away2,
                     group_id, distance, late, earliest, note),
                )
                team_specs.append((club_name, league))

            # Hämta faktiska Turso-ID:n efter INSERT i stället för att lita på lastrowid.
            created_teams = _rows_from_cursor(
                con.execute("SELECT id,name FROM teams WHERE tournament_id=? ORDER BY id", (tid,))
            )
            team_id_by_name = {row["name"]: row["id"] for row in created_teams}
            if len(team_id_by_name) != 8:
                raise RuntimeError(f"Förväntade 8 demolag men hittade {len(team_id_by_name)}.")

            # Andra passet: skapa 14 fiktiva spelare per lag.
            inserted_players = 0
            for club_name, league in team_specs:
                team_id = team_id_by_name[club_name]
                used_names = set()
                numbers = random.sample(range(1, 100), 14)
                for player_index in range(14):
                    while True:
                        player_name = f"{random.choice(star_first_names)} {random.choice(fun_surnames)}"
                        if player_name not in used_names:
                            used_names.add(player_name)
                            break
                    if player_index == 0:
                        position = "Målvakt"
                    else:
                        position = random.choices(
                            ["Försvarare", "Mittfältare", "Anfallare"],
                            weights=[4, 4, 3],
                            k=1,
                        )[0]
                    birth_year = random.randint(2007, 2014)
                    con.execute(
                        "INSERT INTO players(team_id,player_number,name,birth_year,position) VALUES(?,?,?,?,?)",
                        (team_id, numbers[player_index], player_name, birth_year, position),
                    )
                    inserted_players += 1

            # Två fiktiva domare med påhittade kontaktuppgifter och nivåer.
            referee_first_names = ["Bengt", "Arvid", "Mats", "Sara", "Johan", "Linda", "Oskar", "Emma"]
            referee_last_names = ["Domarsson", "Pipström", "Visselberg", "Linjeman", "Rättvik", "Matchlund"]
            referee_levels = ["Distriktsdomare", "Regional domare", "Ungdomsdomare", "Senior domare"]
            used_ref_names = set()
            for ref_index in range(2):
                while True:
                    ref_name = f"{random.choice(referee_first_names)} {random.choice(referee_last_names)}"
                    if ref_name not in used_ref_names:
                        used_ref_names.add(ref_name)
                        break
                phone = f"070-{random.randint(100,999)} {random.randint(10,99)} {random.randint(10,99)}"
                email_local = ref_name.lower().replace(" ", ".").replace("å", "a").replace("ä", "a").replace("ö", "o")
                email = f"{email_local}@demo.cupnavi.se"
                con.execute(
                    "INSERT INTO referees(tournament_id,name,phone,email,referee_level) VALUES(?,?,?,?,?)",
                    (tid, ref_name, phone, email, random.choice(referee_levels)),
                )

            # Kontrollera trupperna innan vi godkänner transaktionen.
            player_check = _one_from_cursor(
                con.execute(
                    """SELECT COUNT(*) AS n
                       FROM players p JOIN teams t ON t.id=p.team_id
                       WHERE t.tournament_id=?""",
                    (tid,),
                )
            )
            if int(player_check["n"] or 0) != inserted_players:
                raise RuntimeError(
                    f"Truppkontrollen misslyckades: skapade {inserted_players}, hittade {player_check['n']}."
                )

            referee_check = _one_from_cursor(
                con.execute("SELECT COUNT(*) AS n FROM referees WHERE tournament_id=?", (tid,))
            )
            if int(referee_check["n"] or 0) < 2:
                raise RuntimeError(
                    f"Domarkontrollen misslyckades: förväntade minst 2 domare, hittade {referee_check['n']}."
                )

            con.commit()
            _clear_render_query_cache()
            st.success(
                f"Demodata skapad: 8 riktiga klubbnamn (3 Allsvenskan, 2 Superettan, 3 Premier League), "
                f"2 grupper, {inserted_players} fiktiva stjärninspirerade spelare och 2 fiktiva domare."
            )
            st.rerun()
        except Exception as exc:
            try:
                con.rollback()
            except Exception:
                pass
            st.error(f"Demodata kunde inte skapas: {exc}")


    st.markdown("##### Testresultat och matchhändelser")
    st.caption(
        "Knapparna nedan fyller redan skapade matcher med slumpade testresultat, mål, assist, "
        "gula kort och röda kort. De är endast avsedda för testning."
    )
    test_col1, test_col2 = st.columns(2)

    if test_col1.button(
        "🎲 Generera resultat – gruppspel",
        use_container_width=True,
        key=f"demo_group_results_{tid}",
    ):
        with st.spinner("Skapar gruppspelsresultat och matchhändelser…", show_time=True):
            generated, stat_rows, warning = _demo_generate_group_results(tid)
        if warning:
            st.warning(warning)
        elif generated:
            st.success(
                f"Testdata skapad för {generated} gruppspelsmatcher. "
                "Mål, assist, gula kort och röda kort har fördelats på testspelarna."
            )
            st.rerun()

    if test_col2.button(
        "🏆 Generera resultat – slutspel",
        use_container_width=True,
        key=f"demo_playoff_results_{tid}",
    ):
        with st.spinner("Spelar igenom slutspel och skapar matchhändelser…", show_time=True):
            generated, stat_rows, warning = _demo_generate_playoff_results(tid)
        if generated:
            st.success(
                f"Testdata skapad för {generated} slutspelsmatcher. "
                "Vinnare har förts vidare och matchhändelser har skapats."
            )
        if warning:
            st.warning(warning)
        if generated:
            st.rerun()


    feedback_rows = all_rows(
        "SELECT created_at,area,message,contact FROM feedback WHERE tournament_id=? ORDER BY id DESC LIMIT 50",
        (tid,),
    )
    with st.expander(f"Feedback från testare ({len(feedback_rows)})"):
        if not feedback_rows:
            st.caption("Ingen feedback har skickats ännu.")
        else:
            for item in feedback_rows:
                st.markdown(f"**{item['area']}** · {item['created_at']}")
                st.write(item["message"])
                if item["contact"]:
                    st.caption(f"Kontakt: {item['contact']}")
                st.divider()


if admin_page == "Kontroller":
    st.header("Kontroller")
    st.caption("Här granskar du blockerande fel och varningar innan turneringen publiceras.")

    with st.expander("Teknisk hälsa och backup", expanded=False):
        st.caption(
            "Det här området är till för drift och felsökning. Det påverkar inte själva turneringsreglerna."
        )
        try:
            with db() as con:
                technical_health = collect_database_health(con)
            hc1, hc2 = st.columns(2)
            health_ok = (
                technical_health["schema_version"] >= REQUIRED_SCHEMA_VERSION
                and not technical_health["missing_tables"]
            )
            hc1.metric(
                "Databasschema",
                f"v{technical_health['schema_version']}",
                help=f"CupNavi {APP_BUILD_VERSION} kräver minst schema v{REQUIRED_SCHEMA_VERSION}.",
            )
            hc2.metric(
                "Teknisk status",
                "OK" if health_ok else "Kontroll krävs",
            )
            if health_ok:
                st.success("✓ Databasen har rätt schema och alla kritiska tabeller finns.")
            else:
                if technical_health["schema_version"] < REQUIRED_SCHEMA_VERSION:
                    st.error(
                        f"Databasschema v{technical_health['schema_version']} används, "
                        f"men appen kräver minst v{REQUIRED_SCHEMA_VERSION}."
                    )
                if technical_health["missing_tables"]:
                    st.error(
                        "Kritiska tabeller saknas: "
                        + ", ".join(technical_health["missing_tables"])
                    )
        except Exception as exc:
            st.error(f"Teknisk hälsokontroll kunde inte köras: {exc}")

        st.divider()
        st.markdown("#### Säkerhetskopia av vald turnering")
        st.caption(
            "Backupen är en portabel JSON-fil med turneringens grunddata, lag, grupper, "
            "spelare, domare, matcher, händelser, erbjudanden och feedback. "
            "Återställning byggs som separat, kontrollerad funktion i nästa stabiliseringsetapp."
        )

        if st.button(
            "Förbered backup",
            key=f"prepare_backup_{tid}",
            use_container_width=True,
        ):
            with st.spinner("CupNavi samlar turneringsdata…"):
                backup_datasets = {
                    "tournaments": [
                        dict(row) for row in all_rows(
                            "SELECT * FROM tournaments WHERE id=?", (tid,)
                        )
                    ],
                    "schedule_rules": [
                        dict(row) for row in all_rows(
                            "SELECT * FROM schedule_rules WHERE tournament_id=?", (tid,)
                        )
                    ],
                    "groups": [
                        dict(row) for row in all_rows(
                            "SELECT * FROM groups WHERE tournament_id=? ORDER BY id", (tid,)
                        )
                    ],
                    "teams": [
                        dict(row) for row in all_rows(
                            "SELECT * FROM teams WHERE tournament_id=? ORDER BY id", (tid,)
                        )
                    ],
                    "players": [
                        dict(row) for row in all_rows(
                            """SELECT p.* FROM players p
                               JOIN teams t ON t.id=p.team_id
                               WHERE t.tournament_id=? ORDER BY p.id""",
                            (tid,),
                        )
                    ],
                    "referees": [
                        dict(row) for row in all_rows(
                            "SELECT * FROM referees WHERE tournament_id=? ORDER BY id", (tid,)
                        )
                    ],
                    "brackets": [
                        dict(row) for row in all_rows(
                            "SELECT * FROM brackets WHERE tournament_id=? ORDER BY id", (tid,)
                        )
                    ],
                    "matches": [
                        dict(row) for row in all_rows(
                            "SELECT * FROM matches WHERE tournament_id=? ORDER BY id", (tid,)
                        )
                    ],
                    "player_match_stats": [
                        dict(row) for row in all_rows(
                            """SELECT s.* FROM player_match_stats s
                               JOIN matches m ON m.id=s.match_id
                               WHERE m.tournament_id=? ORDER BY s.id""",
                            (tid,),
                        )
                    ],
                    "offers": [
                        dict(row) for row in all_rows(
                            "SELECT * FROM offers WHERE tournament_id=? ORDER BY id", (tid,)
                        )
                    ],
                    "sponsors": [
                        dict(row) for row in all_rows(
                            "SELECT * FROM sponsors WHERE tournament_id=? ORDER BY id", (tid,)
                        )
                    ],
                    "functionaries": [
                        dict(row) for row in all_rows(
                            "SELECT * FROM functionaries WHERE tournament_id=? ORDER BY id", (tid,)
                        )
                    ],
                    "visitor_sessions": [
                        dict(row) for row in all_rows(
                            "SELECT * FROM visitor_sessions WHERE tournament_id=? ORDER BY id", (tid,)
                        )
                    ],
                    "feedback": [
                        dict(row) for row in all_rows(
                            "SELECT * FROM feedback WHERE tournament_id=? ORDER BY id", (tid,)
                        )
                    ],
                    "audit_log": [dict(row) for row in all_rows("SELECT * FROM audit_log WHERE tournament_id=? ORDER BY id", (tid,))],
                    "cup_feed": [dict(row) for row in all_rows("SELECT * FROM cup_feed WHERE tournament_id=? ORDER BY id", (tid,))],
                    "notifications": [dict(row) for row in all_rows("SELECT * FROM notifications WHERE tournament_id=? ORDER BY id", (tid,))],
                    "venue_points": [dict(row) for row in all_rows("SELECT * FROM venue_points WHERE tournament_id=? ORDER BY id", (tid,))],
                    "referee_acknowledgements": [dict(row) for row in all_rows("SELECT * FROM referee_acknowledgements WHERE tournament_id=? ORDER BY id", (tid,))],
                }
                backup_bytes, backup_sha = build_backup_bytes(
                    APP_VERSION,
                    tid,
                    backup_datasets,
                )
                st.session_state[f"backup_bytes_{tid}"] = backup_bytes
                st.session_state[f"backup_sha_{tid}"] = backup_sha

        if f"backup_bytes_{tid}" in st.session_state:
            safe_backup_name = re.sub(
                r"[^A-Za-z0-9_-]+",
                "_",
                tournament["name"] or "CupNavi",
            ).strip("_")
            st.success(
                "✓ Backup klar. SHA-256: "
                + st.session_state[f"backup_sha_{tid}"][:16]
                + "…"
            )
            st.download_button(
                "Ladda ner backup",
                data=st.session_state[f"backup_bytes_{tid}"],
                file_name=f"{safe_backup_name}{BACKUP_FILE_SUFFIX}",
                mime="application/json",
                key=f"download_backup_{tid}",
                use_container_width=True,
            )

    with st.expander("📱 Mobilkontroll – Android och iPhone"):
        st.caption("Snabb kontroll före publicering. Testa helst minst en Android/Chrome och en iPhone/Safari.")
        st.markdown(
            """
            - Visningsläge och Admin går att nå utan sidomenyn.
            - Publikflikarna går att svepa horisontellt.
            - Datum- och tidsfält är läsbara och öppnar rätt mobilkontroll.
            - Ingen sida zoomar in automatiskt när ett textfält aktiveras.
            - Tabeller och slutspel går att scrolla utan att hela sidan blir bredare än skärmen.
            - Knappar går att trycka på utan att ligga för tätt.
            """
        )

    with st.expander("⚡ Prestandadiagnostik"):
        st.caption("Mäter databasarbete under den aktuella sidladdningen. Använd siffrorna när en sida känns seg.")
        pc1, pc2, pc3, pc4 = st.columns(4)
        pc1.metric("DB-anrop", _PERF["db_calls"])
        pc2.metric("DB-tid", f"{_PERF['db_ms']:.0f} ms")
        pc3.metric("Cacheträffar", _PERF["cache_hits"])
        pc4.metric("Skrivningar", _PERF["writes"])
        if _PERF["db_calls"] >= 20:
            st.warning("Många databasfrågor på samma sidladdning. Den här sidan bör optimeras vidare.")
        elif _PERF["db_ms"] >= 1500:
            st.warning("Databasen står för en stor del av väntetiden på den här sidladdningen.")
        else:
            st.success("Ingen tydlig databasflaskhals syns i den här mätningen.")
    control_rules = one_row("SELECT * FROM schedule_rules WHERE tournament_id=?", (tid,))
    if control_rules is None:
        run("INSERT INTO schedule_rules(tournament_id) VALUES(?)", (tid,))
        control_rules = one_row("SELECT * FROM schedule_rules WHERE tournament_id=?", (tid,))
    control_errors, control_warnings, control_quality = validate_schedule(tid, tournament, control_rules)
    control_scheduled = one_row(
        "SELECT COUNT(*) AS n FROM matches WHERE tournament_id=? AND scheduled_start IS NOT NULL",
        (tid,),
    )["n"]
    cc1, cc2, cc3 = st.columns(3)
    cc1.metric("Blockerande fel", len(control_errors))
    cc2.metric("Varningar", len(control_warnings))
    cc3.metric("Schemalagda matcher", control_scheduled)
    if not control_scheduled:
        st.info("Det finns ännu inget spelschema att kontrollera. Skapa schemat på fliken Skapa och publicera schema.")
    elif control_errors:
        st.error("Publicering är blockerad tills följande fel är åtgärdade:")
        for message in control_errors:
            st.error(message)
    else:
        st.success("Inga blockerande schemafel hittades.")
    if control_warnings:
        st.warning("Följande varningar behöver granskas före publicering:")
        for message in control_warnings:
            st.warning(message)
    if control_quality:
        st.subheader("Belastning och vila per lag")
        render_centered_table(pd.DataFrame(control_quality))

    unassigned_controls = all_rows("SELECT name FROM teams WHERE tournament_id=? AND group_id IS NULL ORDER BY name", (tid,))
    small_group_controls = []
    group_size_rows = all_rows(
        """SELECT g.id, g.name, COUNT(t.id) AS team_count
           FROM groups g
           LEFT JOIN teams t ON t.group_id=g.id
           WHERE g.tournament_id=?
           GROUP BY g.id, g.name
           ORDER BY g.name""",
        (tid,),
    )
    for group in group_size_rows:
        count = int(group["team_count"] or 0)
        if count < 2:
            small_group_controls.append(f"{group['name']} ({count} lag)")
    st.subheader("Grundkontroller")
    if unassigned_controls:
        st.warning("Lag utan grupp: " + ", ".join(row["name"] for row in unassigned_controls))
    else:
        st.success("Alla registrerade lag är placerade i en grupp.")
    if small_group_controls:
        st.warning("Grupper med färre än två lag: " + ", ".join(small_group_controls))
    else:
        st.success("Alla skapade grupper har minst två lag.")


if admin_page == "Lag":
    st.header("Lag")
    st.caption("Registrera lagen först. Varje hemma- och bortaställ kan vara helfärgat, randigt, rutigt eller delat och ha upp till två färger. Här anger du även resväg och önskemål om en senare första match. Gruppindelningen görs därefter under fliken Grupper.")
    max_teams = int(tournament["expected_team_count"] or 0)
    registered_team_count = one_row("SELECT COUNT(*) AS n FROM teams WHERE tournament_id=?", (tid,))["n"]
    if max_teams:
        st.info(f"Registrerade lag: {registered_team_count} av maximalt {max_teams}.")
    team_limit_reached = bool(max_teams and registered_team_count >= max_teams)
    if team_limit_reached:
        st.info(
            f"Maximalt antal lag ({max_teams}) är registrerade. "
            "Om du vill lägga till fler lag måste du först ändra planerat antal lag under Admin → Översikt."
        )
    if team_limit_reached:
        st.warning(f"Maximalt antal lag ({max_teams}) är registrerade. Ändra planerat antal lag under Admin → Översikt om fler lag ska kunna läggas till.")
    with st.container(border=True):
        team_name = st.text_input("Lagnamn")
        st.markdown("#### Hemmaställ")
        hc1, hc2, hc3 = st.columns([1.2, 1, 1])
        home_pattern = hc1.selectbox("Mönster hemma", KIT_PATTERNS, key="new_home_pattern")
        primary = hc2.color_picker("Hemma – färg 1", "#111827")
        home_color_2 = hc3.color_picker("Hemma – färg 2", "#FFFFFF", help="Används när stället inte är helfärgat.")
        st.markdown(kit_preview_html(home_pattern, primary, home_color_2, "Förhandsvisning hemmaställ"), unsafe_allow_html=True)

        st.markdown("#### Bortaställ")
        ac1, ac2, ac3 = st.columns([1.2, 1, 1])
        away_pattern = ac1.selectbox("Mönster borta", KIT_PATTERNS, key="new_away_pattern")
        secondary = ac2.color_picker("Borta – färg 1", "#FFFFFF")
        away_color_2 = ac3.color_picker("Borta – färg 2", "#111827", help="Används när stället inte är helfärgat.")
        st.markdown(kit_preview_html(away_pattern, secondary, away_color_2, "Förhandsvisning bortaställ"), unsafe_allow_html=True)

        st.markdown("#### Ansvarig kontaktperson")
        rc1, rc2, rc3 = st.columns(3)
        responsible_name = rc1.text_input("Namn", key=f"new_team_responsible_name_{tid}")
        responsible_phone = rc2.text_input("Telefon", key=f"new_team_responsible_phone_{tid}")
        responsible_email = rc3.text_input("E-post", key=f"new_team_responsible_email_{tid}")
        responsible_protected = st.checkbox(
            "Skyddade kontaktuppgifter – visas aldrig publikt",
            value=True,
            key=f"new_team_responsible_protected_{tid}",
        )
        distance = st.number_input("Resväg i kilometer", 0, 5000, 0)
        travel_note = st.text_input("Resekommentar", placeholder="Exempel: Reser samma morgon")
        late_first_match = st.checkbox("Önskar senare första match", help="Använd detta exempelvis för lag med lång resväg.")
        earliest_first_time = st.time_input("Första match tidigast", value=datetime.strptime("10:00", "%H:%M").time(), help="Tiden används bara om Önskar senare första match är markerat.")
        if st.button("Lägg till lag", type="primary", disabled=team_limit_reached, key=f"add_team_{tid}"):
            current_count = one_row("SELECT COUNT(*) AS n FROM teams WHERE tournament_id=?", (tid,))["n"]
            if max_teams and current_count >= max_teams:
                st.error(f"Det går inte att lägga till fler än {max_teams} lag i den här turneringen.")
            elif team_name.strip():
                try:
                    new_team_id = insert_team_with_limit(
                        tid,
                        team_name.strip(),
                        primary,
                        secondary,
                        home_pattern,
                        home_color_2,
                        away_pattern,
                        away_color_2,
                        distance,
                        late_first_match,
                        earliest_first_time.strftime("%H:%M") if late_first_match else None,
                        travel_note.strip(),
                    )
                    run(
                        "UPDATE teams SET responsible_name=?,responsible_phone=?,responsible_email=?,responsible_contact_protected=? WHERE id=?",
                        (responsible_name.strip(), responsible_phone.strip(), responsible_email.strip(), int(responsible_protected), new_team_id),
                    )
                    st.rerun()
                except TeamLimitReachedError as exc:
                    hard_max = int(exc.args[0]) if exc.args else max_teams
                    st.error(f"Det går inte att lägga till fler än {hard_max} lag i den här turneringen.")
                except sqlite3.IntegrityError as exc:
                    if "TEAM_LIMIT_REACHED" in str(exc):
                        fresh_limit = one_row("SELECT expected_team_count FROM tournaments WHERE id=?", (tid,))
                        hard_max = int(fresh_limit["expected_team_count"] or 0) if fresh_limit else max_teams
                        st.error(f"Det går inte att lägga till fler än {hard_max} lag i den här turneringen.")
                    else:
                        raise
            else:
                st.error("Ange ett lagnamn.")

    teams = all_rows("SELECT * FROM teams WHERE tournament_id=? ORDER BY name", (tid,))
    st.divider()
    st.subheader("Skapade lag")
    if teams:
        group_names = {
            row["id"]: row["name"]
            for row in all_rows("SELECT id,name FROM groups WHERE tournament_id=? ORDER BY name", (tid,))
        }
        render_centered_table(
            pd.DataFrame([
                {
                    "Lag": team_row["name"],
                    "Grupp": group_names.get(team_row["group_id"], "Ej placerad"),
                    "Ansvarig": _team_value(team_row, "responsible_name", "") or "–",
                    "Telefon": _team_value(team_row, "responsible_phone", "") or "–",
                    "E-post": _team_value(team_row, "responsible_email", "") or "–",
                    "Skyddad": "Ja" if bool(_team_value(team_row, "responsible_contact_protected", 1)) else "Nej",
                    "Resväg km": team_row["distance_km"] or 0,
                }
                for team_row in teams
            ])
        )
    else:
        st.info("Inga lag är skapade ännu.")

    if teams:
        st.divider()
        st.subheader("✅ Digital lagincheckning")
        st.caption("Markera vilka lag som är på plats. Statusen sparas med tidsstämpel och syns direkt för tävlingsledningen.")
        checkin_df = pd.DataFrame([
            {"team_id": row["id"], "Lag": row["name"], "På plats": bool(row["checked_in"]), "Incheckad": row["checked_in_at"] or ""}
            for row in teams
        ])
        edited_checkins = st.data_editor(
            checkin_df, hide_index=True, use_container_width=True,
            disabled=["team_id", "Lag", "Incheckad"],
            column_order=["Lag", "På plats", "Incheckad"],
            column_config={"På plats": st.column_config.CheckboxColumn("På plats")},
            key=f"team_checkins_{tid}",
        )
        if st.button("Spara incheckning", key=f"save_checkins_{tid}", type="primary", use_container_width=True):
            changed = 0
            original = {int(row["id"]): row for row in teams}
            now_iso = datetime.now().isoformat(timespec="seconds")
            with db() as con:
                for _, edited_row in edited_checkins.iterrows():
                    team_id = int(edited_row["team_id"])
                    new_value = 1 if bool(edited_row["På plats"]) else 0
                    old_value = int(original[team_id]["checked_in"] or 0)
                    if new_value == old_value:
                        continue
                    changed += 1
                    con.execute(
                        "UPDATE teams SET checked_in=?,checked_in_at=?,checked_in_by=? WHERE id=?",
                        (new_value, now_iso if new_value else None, "Admin" if new_value else None, team_id),
                    )
                con.commit()
            if changed:
                _clear_render_query_cache()
                for _, edited_row in edited_checkins.iterrows():
                    team_id = int(edited_row["team_id"]); new_value = 1 if bool(edited_row["På plats"]) else 0
                    old_value = int(original[team_id]["checked_in"] or 0)
                    if new_value != old_value:
                        team_name = original[team_id]["name"]
                        record_audit(tid, "team_checkin", "team", f"{team_name}: {'incheckad' if new_value else 'incheckning borttagen'}",
                                     entity_id=team_id, before={"checked_in": old_value}, after={"checked_in": new_value}, reversible=False)
                st.success(f"Incheckning uppdaterad för {changed} lag.")
                st.rerun()
            else:
                st.info("Inga ändringar att spara.")

        st.divider()
        st.subheader("🔐 Lagportal – koder")
        st.caption("Här ser administratören alla aktuella lagkoder. Inloggningen verifieras fortfarande mot en saltad hash. Skydda tabellen från obehöriga.")
        credentials = {
            int(row["team_id"]): row
            for row in all_rows(
                "SELECT team_id,admin_code,created_at,rotated_at FROM participant_access_credentials WHERE tournament_id=?",
                (tid,),
            )
        }
        code_rows = []
        missing_display_codes = []
        for team_row in teams:
            cred = credentials.get(int(team_row["id"]))
            visible_code = (cred["admin_code"] if cred else None) or ""
            if not visible_code:
                missing_display_codes.append(int(team_row["id"]))
            code_rows.append({
                "Lag": team_row["name"],
                "Lagkod": visible_code or ("Äldre kod – skapa ny" if cred else "Saknas"),
                "Senast ändrad": (cred["rotated_at"] or cred["created_at"]) if cred else "–",
            })
        render_centered_table(pd.DataFrame(code_rows))
        if missing_display_codes:
            st.warning(f"{len(missing_display_codes)} lag saknar en visningsbar kod. Äldre hashade koder kan inte återläsas.")
            if st.button("Skapa/ersätt koder för alla som saknar visningsbar kod", key=f"generate_missing_portal_codes_{tid}", type="primary", use_container_width=True):
                now_iso = datetime.now().isoformat(timespec="seconds")
                with db() as con:
                    for missing_team_id in missing_display_codes:
                        plain_code = generate_access_code()
                        salt, code_hash = new_code_hash(plain_code)
                        con.execute(
                            """INSERT INTO participant_access_credentials(tournament_id,team_id,code_salt,code_hash,created_at,rotated_at,admin_code)
                               VALUES(?,?,?,?,?,NULL,?)
                               ON CONFLICT(tournament_id,team_id) DO UPDATE SET code_salt=excluded.code_salt,code_hash=excluded.code_hash,rotated_at=excluded.created_at,admin_code=excluded.admin_code""",
                            (tid, missing_team_id, salt, code_hash, now_iso, plain_code),
                        )
                    con.commit()
                _clear_render_query_cache()
                st.success("Koder skapades. Tidigare koder för berörda lag är nu ogiltiga.")
                st.rerun()

        access_team_id = st.selectbox(
            "Lag för att skapa/återställa kod",
            [row["id"] for row in teams],
            format_func=lambda selected_id: next(row["name"] for row in teams if row["id"] == selected_id),
            key=f"portal_access_team_{tid}",
        )
        credential = one_row("SELECT id,admin_code FROM participant_access_credentials WHERE tournament_id=? AND team_id=?", (tid, access_team_id))
        if st.button("Skapa ny kod" if not credential else "Återställ och skapa ny kod", key=f"generate_portal_code_{tid}_{access_team_id}", type="primary"):
            plain_code = generate_access_code()
            salt, code_hash = new_code_hash(plain_code)
            now_iso = datetime.now().isoformat(timespec="seconds")
            run(
                """INSERT INTO participant_access_credentials(tournament_id,team_id,code_salt,code_hash,created_at,rotated_at,admin_code)
                   VALUES(?,?,?,?,?,NULL,?)
                   ON CONFLICT(tournament_id,team_id) DO UPDATE SET code_salt=excluded.code_salt,code_hash=excluded.code_hash,rotated_at=excluded.created_at,admin_code=excluded.admin_code""",
                (tid, access_team_id, salt, code_hash, now_iso, plain_code),
            )
            record_audit(tid, "participant_code_rotated", "team", "Ny portal-kod skapad", entity_id=access_team_id, actor="Admin")
            st.success(f"Ny lagkod: **{plain_code}**")
            st.rerun()

    st.divider()
    st.markdown(
        """
        <div style="
            background:#ffffff;
            border:1px solid #cbd5e1;
            border-left:5px solid #166534;
            border-radius:10px;
            padding:12px 16px;
            margin:6px 0 12px 0;
            color:#0f172a;
            font-size:1.08rem;
            font-weight:800;">
            Redigera eller ta bort lag
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.container(border=True):
        if teams:
            edit_team_id = st.selectbox("Välj lag", [t["id"] for t in teams], format_func=lambda x: next(t["name"] for t in teams if t["id"] == x), key="edit_team")
            edit_team = next(t for t in teams if t["id"] == edit_team_id)
            with st.container(border=True):
                edited_name = st.text_input("Lagnamn", value=edit_team["name"], key=f"edit_name_{edit_team_id}")
                st.markdown("#### Hemmaställ")
                eh1, eh2, eh3 = st.columns([1.2, 1, 1])
                saved_home_pattern = _team_value(edit_team, "home_pattern", "Helfärgad")
                edited_home_pattern = eh1.selectbox(
                    "Mönster hemma", KIT_PATTERNS,
                    index=KIT_PATTERNS.index(saved_home_pattern) if saved_home_pattern in KIT_PATTERNS else 0,
                    key=f"edit_home_pattern_{edit_team_id}",
                )
                edited_primary = eh2.color_picker("Hemma – färg 1", edit_team["primary_color"], key=f"edit_home_color1_{edit_team_id}")
                edited_home_color_2 = eh3.color_picker("Hemma – färg 2", _team_value(edit_team, "home_color_2", "#FFFFFF"), key=f"edit_home_color2_{edit_team_id}")
                st.markdown(kit_preview_html(edited_home_pattern, edited_primary, edited_home_color_2, "Hemmaställ"), unsafe_allow_html=True)

                st.markdown("#### Bortaställ")
                ea1, ea2, ea3 = st.columns([1.2, 1, 1])
                saved_away_pattern = _team_value(edit_team, "away_pattern", "Helfärgad")
                edited_away_pattern = ea1.selectbox(
                    "Mönster borta", KIT_PATTERNS,
                    index=KIT_PATTERNS.index(saved_away_pattern) if saved_away_pattern in KIT_PATTERNS else 0,
                    key=f"edit_away_pattern_{edit_team_id}",
                )
                edited_secondary = ea2.color_picker("Borta – färg 1", edit_team["secondary_color"], key=f"edit_away_color1_{edit_team_id}")
                edited_away_color_2 = ea3.color_picker("Borta – färg 2", _team_value(edit_team, "away_color_2", "#111827"), key=f"edit_away_color2_{edit_team_id}")
                st.markdown(kit_preview_html(edited_away_pattern, edited_secondary, edited_away_color_2, "Bortaställ"), unsafe_allow_html=True)

                st.markdown("#### Ansvarig kontaktperson")
                erc1, erc2, erc3 = st.columns(3)
                edited_responsible_name = erc1.text_input("Namn", value=_team_value(edit_team, "responsible_name", "") or "", key=f"edit_responsible_name_{edit_team_id}")
                edited_responsible_phone = erc2.text_input("Telefon", value=_team_value(edit_team, "responsible_phone", "") or "", key=f"edit_responsible_phone_{edit_team_id}")
                edited_responsible_email = erc3.text_input("E-post", value=_team_value(edit_team, "responsible_email", "") or "", key=f"edit_responsible_email_{edit_team_id}")
                edited_responsible_protected = st.checkbox(
                    "Skyddade kontaktuppgifter – visas aldrig publikt",
                    value=bool(_team_value(edit_team, "responsible_contact_protected", 1)),
                    key=f"edit_responsible_protected_{edit_team_id}",
                )
                edited_distance = st.number_input("Resväg i kilometer", 0, 5000, int(edit_team["distance_km"] or 0), key=f"edit_distance_{edit_team_id}")
                edited_travel_note = st.text_input("Resekommentar", value=edit_team["travel_note"] or "", key=f"edit_travel_note_{edit_team_id}")
                edited_late_first = st.checkbox("Önskar senare första match", value=bool(edit_team["late_first_match"]), key=f"edit_late_first_{edit_team_id}")
                saved_earliest = edit_team["earliest_first_time"] or "10:00"
                edited_earliest = st.time_input(
                    "Första match tidigast",
                    value=datetime.strptime(saved_earliest, "%H:%M").time(),
                    help="Tiden används bara om Önskar senare första match är markerat.",
                    key=f"edit_earliest_{edit_team_id}",
                )
                if st.button("Spara ändringar", type="primary", key=f"save_team_{edit_team_id}"):
                    if edited_name.strip():
                        run(
                            """UPDATE teams SET
                                name=?,primary_color=?,secondary_color=?,home_pattern=?,home_color_2=?,away_pattern=?,away_color_2=?,
                                distance_km=?,late_first_match=?,earliest_first_time=?,travel_note=?,kit_confirmed_at=NULL,
                                responsible_name=?,responsible_phone=?,responsible_email=?,responsible_contact_protected=? WHERE id=?""",
                            (edited_name.strip(), edited_primary, edited_secondary,
                             edited_home_pattern, edited_home_color_2, edited_away_pattern, edited_away_color_2,
                             edited_distance, int(edited_late_first), edited_earliest.strftime("%H:%M") if edited_late_first else None,
                             edited_travel_note.strip(), edited_responsible_name.strip(), edited_responsible_phone.strip(),
                             edited_responsible_email.strip(), int(edited_responsible_protected), edit_team_id),
                        )
                        st.rerun()
                    st.error("Lagnamnet får inte vara tomt.")
            confirm_team_delete = st.checkbox("Jag förstår att lagets trupp, statistik och berörda matcher tas bort", key=f"confirm_team_{edit_team_id}")
            if st.button("Ta bort laget", disabled=not confirm_team_delete, key=f"delete_team_{edit_team_id}"):
                token = f"team:{edit_team_id}"
                bracket_ids = [r["bracket_id"] for r in all_rows("SELECT DISTINCT bracket_id FROM matches WHERE bracket_id IS NOT NULL AND (home_source=? OR away_source=?)", (token, token))]
                if edit_team["group_id"]:
                    group_brackets = all_rows(
                        "SELECT DISTINCT bracket_id FROM matches WHERE bracket_id IS NOT NULL AND (home_source LIKE ? OR away_source LIKE ?)",
                        (f"group:{edit_team['group_id']}:%", f"group:{edit_team['group_id']}:%"),
                    )
                    bracket_ids.extend(r["bracket_id"] for r in group_brackets)
                with db() as con:
                    con.execute("DELETE FROM matches WHERE home_source=? OR away_source=?", (token, token))
                    for bracket_id in set(bracket_ids):
                        con.execute("DELETE FROM brackets WHERE id=?", (bracket_id,))
                    con.execute("DELETE FROM teams WHERE id=?", (edit_team_id,))
                    con.commit()
                st.rerun()
        else:
            st.info("Det finns inga lag att redigera.")


if admin_page == "Grupper":
    st.header("Grupper")
    st.caption("Skapa gruppindelningen efter att lagen är registrerade och placera sedan varje lag i rätt grupp.")
    st.subheader("Grupper")
    teams = all_rows("SELECT * FROM teams WHERE tournament_id=? ORDER BY name", (tid,))
    if not teams:
        st.warning("Lägg först till lagen under fliken Lag innan du skapar grupper.")
    with st.form("new_group", clear_on_submit=True):
        group_name = st.text_input("Gruppnamn", placeholder="Grupp A")
        if st.form_submit_button("Lägg till grupp", type="primary", disabled=not bool(teams)):
            if group_name.strip():
                run("INSERT INTO groups(tournament_id,name) VALUES(?,?)", (tid, group_name.strip()))
                st.rerun()
            st.error("Ange ett gruppnamn.")

    groups = all_rows("SELECT * FROM groups WHERE tournament_id=? ORDER BY name", (tid,))
    if groups:
        st.caption("Skapade grupper: " + ", ".join(g["name"] for g in groups))

    st.divider()
    st.subheader("Placera lagen i rätt grupp")
    if not teams:
        st.info("Inga lag är registrerade.")
    elif not groups:
        st.info("Skapa minst en grupp ovan för att kunna placera lagen.")
    elif sort_items is not None:
        st.caption("Dra lagen mellan rutorna och klicka sedan på Spara gruppindelning.")
        sortable_team_labels = {
            t["id"]: t["name"] + "\u2063" + "".join("\u200b" if bit == "0" else "\u200c" for bit in bin(t["id"])[2:])
            for t in teams
        }
        team_id_by_item = {label: team_id for team_id, label in sortable_team_labels.items()}
        containers = [{"header": "Ej placerade", "items": [sortable_team_labels[t["id"]] for t in teams if t["group_id"] is None]}]
        for g in groups:
            containers.append({"header": g["name"], "items": [sortable_team_labels[t["id"]] for t in teams if t["group_id"] == g["id"]]})
        sorted_containers = sort_items(
            containers,
            multi_containers=True,
            key=(
                f"team_group_sort_{tid}_"
                f"g{'_'.join(str(g['id']) for g in groups)}_"
                f"t{'_'.join(str(t['id']) for t in teams)}"
            ),
            custom_style="""
            .sortable-container { border: 1px solid #d1d5db; border-radius: 8px; }
            .sortable-container-header { font-weight: 700; padding: 8px; }
            .sortable-item { background: #f3f4f6; color: #111827; border-radius: 6px; margin: 5px; }
            """,
        )
        if st.button("Spara gruppindelning", type="primary"):
            group_by_name = {g["name"]: g["id"] for g in groups}
            with db() as con:
                for container in sorted_containers:
                    target_group = group_by_name.get(container["header"])
                    for item in container["items"]:
                        selected_team_id = team_id_by_item[item]
                        con.execute("UPDATE teams SET group_id=? WHERE id=?", (target_group, selected_team_id))
                con.commit()
            st.success("Gruppindelningen sparades.")
            st.rerun()
    else:
        st.warning("Dra-och-släpp kräver tillägget streamlit-sortables. Reservläget används tills det installerats.")
        for t in teams:
            c1, c2, c3 = st.columns([4, 3, 2])
            c1.markdown(f"**{t['name']}**")
            options = [None] + [g["id"] for g in groups]
            current_index = options.index(t["group_id"]) if t["group_id"] in options else 0
            new_group = c2.selectbox("Grupp", options, index=current_index, key=f"group_{t['id']}", label_visibility="collapsed", format_func=lambda x: "Ingen grupp" if x is None else next(g["name"] for g in groups if g["id"] == x))
            if c3.button("Spara", key=f"save_group_{t['id']}"):
                run("UPDATE teams SET group_id=? WHERE id=?", (new_group, t["id"]))
                st.rerun()

    st.divider()
    with st.expander("Redigera eller ta bort grupp"):
        if groups:
            edit_group_id = st.selectbox("Välj grupp", [g["id"] for g in groups], format_func=lambda x: next(g["name"] for g in groups if g["id"] == x), key="edit_group")
            edit_group = next(g for g in groups if g["id"] == edit_group_id)
            with st.form("edit_group_form"):
                edited_group_name = st.text_input("Gruppnamn", value=edit_group["name"])
                if st.form_submit_button("Spara gruppnamn", type="primary"):
                    if edited_group_name.strip():
                        run("UPDATE groups SET name=? WHERE id=?", (edited_group_name.strip(), edit_group_id))
                        st.rerun()
                    st.error("Gruppnamnet får inte vara tomt.")
            confirm_group_delete = st.checkbox("Jag förstår att gruppens matcher och slutspel som använder gruppen tas bort, och att lagen blir oplacerade", key=f"confirm_group_{edit_group_id}")
            if st.button("Ta bort gruppen", disabled=not confirm_group_delete, key=f"delete_group_{edit_group_id}"):
                affected_brackets = [r["bracket_id"] for r in all_rows("SELECT DISTINCT bracket_id FROM matches WHERE bracket_id IS NOT NULL AND (home_source LIKE ? OR away_source LIKE ?)", (f"group:{edit_group_id}:%", f"group:{edit_group_id}:%"))]
                with db() as con:
                    con.execute("UPDATE teams SET group_id=NULL WHERE group_id=?", (edit_group_id,))
                    for bracket_id in affected_brackets:
                        con.execute("DELETE FROM brackets WHERE id=?", (bracket_id,))
                    con.execute("DELETE FROM groups WHERE id=?", (edit_group_id,))
                    con.commit()
                st.rerun()
        else:
            st.info("Det finns inga grupper att redigera.")


if admin_page == "Trupper":
    st.header("Trupper")
    st.caption("Registrera spelare och truppuppgifter för respektive lag. Här styr du också reglerna för lagens egna trupp- och matchtruppsregistrering.")
    with st.expander("⚙️ Regler för Lagportal och matchtrupper", expanded=False):
        rc1, rc2 = st.columns(2)
        portal_max_roster = rc1.number_input("Max spelare i truppen (0 = ingen gräns)", 0, 200, int(_row_value(tournament, "max_roster_size", 0) or 0), key=f"max_roster_{tid}")
        portal_deadline = rc2.number_input("Matchtrupp låses minuter före match", 0, 1440, int(_row_value(tournament, "squad_deadline_minutes", 30) or 30), key=f"squad_deadline_{tid}")
        portal_public_contact = st.checkbox("Tillåt lagledare/deltagaransvarig att ange en publik kontaktperson", value=bool(_row_value(tournament, "allow_team_public_contact", 0)), key=f"allow_public_contact_{tid}")
        if st.button("Spara portalregler", key=f"save_portal_rules_{tid}", type="primary"):
            run("UPDATE tournaments SET max_roster_size=?,squad_deadline_minutes=?,allow_team_public_contact=? WHERE id=?", (portal_max_roster, portal_deadline, int(portal_public_contact), tid))
            st.success("Portalreglerna är sparade.")
            st.rerun()
    teams = all_rows("SELECT * FROM teams WHERE tournament_id=? ORDER BY name", (tid,))
    if not teams:
        st.info("Lägg först till ett lag.")
    else:
        team_id = st.selectbox("Välj lag", [t["id"] for t in teams], format_func=lambda x: next(t["name"] for t in teams if t["id"] == x))
        with st.form("new_player", clear_on_submit=True):
            c1, c2, c3, c4 = st.columns(4)
            pname = c1.text_input("Spelare")
            number = c2.number_input("Tröjnummer", 0, 99, 0)
            birth = c3.number_input("Födelseår", 1980, 2030, 2014)
            position = c4.selectbox("Position", ["Målvakt", "Försvarare", "Mittfältare", "Anfallare", "Ej angiven"])
            if st.form_submit_button("Lägg till spelare", type="primary"):
                if pname.strip():
                    run("INSERT INTO players(team_id,player_number,name,birth_year,position) VALUES(?,?,?,?,?)", (team_id, number, pname.strip(), birth, position))
                    st.rerun()
                st.error("Ange spelarens namn.")
        players = all_rows("SELECT * FROM players WHERE team_id=? ORDER BY player_number,name", (team_id,))
        render_centered_table(pd.DataFrame([{"Nr": p["player_number"], "Spelare": p["name"], "Födelseår": p["birth_year"], "Position": p["position"]} for p in players]))

        st.markdown("#### Matchtrupper – admin")
        admin_team_matches = [
            row for row in all_rows("SELECT * FROM matches WHERE tournament_id=? AND scheduled_start IS NOT NULL ORDER BY scheduled_start,id", (tid,))
            if team_id in _match_team_ids(row)
        ]
        if not admin_team_matches:
            st.info("Laget har ännu inga schemalagda matcher.")
        elif not players:
            st.info("Lägg till spelare innan matchtrupp kan registreras.")
        else:
            admin_match_id = st.selectbox("Välj match för matchtrupp", [row["id"] for row in admin_team_matches], format_func=lambda mid: _portal_match_label(next(row for row in admin_team_matches if row["id"] == mid)), key=f"admin_squad_match_{team_id}")
            existing_admin_squad = {int(row["player_id"]) for row in all_rows("SELECT player_id FROM match_rosters WHERE match_id=? AND team_id=?", (admin_match_id, team_id))}
            admin_player_ids = [int(row["id"]) for row in players]
            admin_selected = st.multiselect(
                "Spelare i matchtruppen",
                admin_player_ids,
                default=[pid for pid in admin_player_ids if pid in existing_admin_squad],
                format_func=lambda pid: next(f"#{row['player_number'] if row['player_number'] is not None else '–'} {row['name']}" for row in players if int(row["id"]) == int(pid)),
                key=f"admin_match_roster_{admin_match_id}_{team_id}",
            )
            if st.button("Spara matchtrupp som admin", key=f"admin_save_squad_{admin_match_id}_{team_id}", type="primary"):
                _save_match_roster(admin_match_id, team_id, admin_selected, "Admin")
                record_audit(tid, "match_roster_saved", "match", f"Admin sparade matchtrupp för {next(row['name'] for row in teams if row['id'] == team_id)}", entity_id=admin_match_id, actor="Admin")
                st.success("Matchtruppen är sparad. Admin kan ändra även efter deadline.")
                st.rerun()


if admin_page == "Domare":
    st.header("Domare")
    st.caption("Registrera domare som kan tilldelas matcher automatiskt eller manuellt.")
    with st.form("new_referee", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        rname = c1.text_input("Namn")
        phone = c2.text_input("Telefon")
        email = c3.text_input("E-post")
        if st.form_submit_button("Lägg till domare", type="primary"):
            if rname.strip():
                run("INSERT INTO referees(tournament_id,name,phone,email) VALUES(?,?,?,?)", (tid, rname.strip(), phone.strip(), email.strip()))
                st.rerun()
            st.error("Ange domarens namn.")
    refs = all_rows("SELECT * FROM referees WHERE tournament_id=? ORDER BY name", (tid,))
    render_centered_table(pd.DataFrame([{"Namn": r["name"], "Telefon": r["phone"], "E-post": r["email"]} for r in refs]))


if admin_page == "Skapa och publicera schema":
    st.header("Skapa och publicera schema")
    st.caption("En knapp skapar alla gruppmöten och schemalägger dem samtidigt för samtliga grupper. Kontrollresultaten finns på fliken Kontroller.")
    if "schedule_message" in st.session_state:
        message_type, message_text = st.session_state.pop("schedule_message")
        getattr(st, message_type)(message_text)

    st.markdown("#### 1. Sparat regelverk")
    rules = one_row("SELECT * FROM schedule_rules WHERE tournament_id=?", (tid,))
    if rules is None:
        run("INSERT INTO schedule_rules(tournament_id) VALUES(?)", (tid,))
        rules = one_row("SELECT * FROM schedule_rules WHERE tournament_id=?", (tid,))
    match_minutes = (rules["halves"] * rules["minutes_per_half"]) + ((rules["halves"] - 1) * rules["halftime_minutes"])
    consecutive_rule_text = (
        f"försök undvika följdmatcher, extra paus {rules['consecutive_match_break_minutes']} min om det inte går"
        if rules["avoid_consecutive_matches"] else "följdmatcher tillåtna"
    )
    st.info(
        f"{rules['halves']} × {rules['minutes_per_half']} minuter · halvtidspaus {rules['halftime_minutes']} min · "
        f"matchtid totalt {match_minutes} min · första avspark {rules['first_match_time']} · sista plantid {rules['latest_kickoff_time']} · "
        f"{rules['pitch_count']} planer · {consecutive_rule_text} · domare: {rules['referee_mode']}."
    )
    st.caption("Regelverket och slutspelsformatet ändras under Adminöversikt → Cupens grunduppgifter.")
    schedule_groups = all_rows("SELECT id,name FROM groups WHERE tournament_id=? ORDER BY name", (tid,))
    schedule_teams = all_rows("SELECT id,group_id FROM teams WHERE tournament_id=?", (tid,))
    unassigned_count = sum(1 for team_row in schedule_teams if team_row["group_id"] is None)
    too_small_groups = [
        group["name"] for group in schedule_groups
        if one_row("SELECT COUNT(*) AS n FROM teams WHERE group_id=?", (group["id"],))["n"] < 2
    ]
    group_match_total = one_row("SELECT COUNT(*) AS n FROM matches WHERE tournament_id=? AND stage='Gruppspel'", (tid,))["n"]
    unscheduled_group_total = one_row("SELECT COUNT(*) AS n FROM matches WHERE tournament_id=? AND stage='Gruppspel' AND scheduled_start IS NULL", (tid,))["n"]
    scheduled_total = one_row("SELECT COUNT(*) AS n FROM matches WHERE tournament_id=? AND scheduled_start IS NOT NULL", (tid,))["n"]
    unpublished_total = one_row("SELECT COUNT(*) AS n FROM matches WHERE tournament_id=? AND scheduled_start IS NOT NULL AND schedule_published=0", (tid,))["n"]
    played_result_total = one_row(
        "SELECT COUNT(*) AS n FROM matches WHERE tournament_id=? AND home_score IS NOT NULL AND away_score IS NOT NULL",
        (tid,),
    )["n"]
    schedule_errors, schedule_warnings, schedule_quality = validate_schedule(tid, tournament, rules)
    playoff_specs, playoff_setup_error = playoff_specs_for_tournament(tid, tournament)
    playoff_model_ready = bool(tournament["playoff_model_confirmed"])

    st.markdown("#### 2. Skapa och generera hela spelschemat")
    with st.container(border=True):
        status1, status2, status3 = st.columns(3)
        status1.metric("Gruppspelsmatcher", group_match_total)
        status2.metric("Schemalagda matcher", scheduled_total)
        status3.metric("Ej publicerade", unpublished_total)
        create_disabled = (
            not schedule_groups
            or unassigned_count > 0
            or bool(too_small_groups)
            or not playoff_model_ready
            or bool(playoff_setup_error)
        )
        schedule_button_label = (
            "Regenerera återstående grupp- och slutspelsmatcher utan att ändra spelade matcher"
            if played_result_total else "Skapa gruppspel + slutspel och generera hela spelschemat"
        )
        if st.button(schedule_button_label, type="primary", use_container_width=True, disabled=create_disabled):
            started_schedule = time.perf_counter()
            try:
                with st.spinner("CupNavi bygger schemat och fördelar planer/domare…"):
                    if played_result_total:
                        created, ready_groups, skipped_groups = 0, len(schedule_groups), []
                        optimize_group_home_away(tid)
                        playoff_ok, playoff_error = ensure_playoffs_for_schedule(tid, tournament)
                        if not playoff_ok:
                            raise RuntimeError(playoff_error)
                        count, unresolved, warning = generate_schedule(tid, tournament, rules, preserve_existing=True)
                        parts = [
                            f"{played_result_total} färdigspelade matcher skyddades och lämnades oförändrade.",
                            "Slutspelsträdet kontrollerades och uppdaterades automatiskt.",
                            f"{count} återstående matcher schemalades.",
                        ]
                    else:
                        created, ready_groups, skipped_groups = create_all_group_matches(tid)
                        playoff_ok, playoff_error = ensure_playoffs_for_schedule(tid, tournament)
                        if not playoff_ok:
                            raise RuntimeError(playoff_error)
                        count, unresolved, warning = generate_schedule(tid, tournament, rules)
                        parts = [
                            f"Alla {ready_groups} grupper kontrollerades och {created} saknade gruppmatcher skapades.",
                            "Slutspelsmatcherna skapades automatiskt utifrån vald slutspelsmodell.",
                            f"{count} matcher schemalades totalt.",
                        ]
                elapsed = time.perf_counter() - started_schedule
                parts.append(f"Genereringen tog {elapsed:.1f} sekunder.")
                if unresolved:
                    parts.append(f"{unresolved} matcher kunde inte schemaläggas.")
                if warning:
                    parts.append(warning)
                st.session_state["schedule_message"] = (
                    "warning" if unresolved or warning else "success",
                    " ".join(parts),
                )
            except Exception as exc:
                elapsed = time.perf_counter() - started_schedule
                st.session_state["schedule_message"] = (
                    "error",
                    f"Schemagenereringen avbröts efter {elapsed:.1f} sekunder: {exc}",
                )
            st.rerun()
        if played_result_total:
            st.info(
                f"Det finns {played_result_total} matcher med registrerat resultat. "
                "Därför bevaras befintliga schematider och resultat; endast återstående matcher får nya tider."
            )
        if create_disabled:
            problems = []
            if not schedule_groups:
                problems.append("skapa minst en grupp")
            if unassigned_count:
                problems.append(f"placera {unassigned_count} lag i en grupp")
            if too_small_groups:
                problems.append("lägg minst två lag i: " + ", ".join(too_small_groups))
            if not playoff_model_ready:
                problems.append("välj och spara slutspelsmodell på Adminöversikten")
            if playoff_setup_error:
                problems.append(playoff_setup_error)
            st.warning("Innan hela spelschemat kan skapas måste du " + "; ".join(problems) + ".")
        elif scheduled_total == 0:
            st.info("Klicka på knappen ovan för att skapa gruppspel, slutspel och generera hela spelschemat i ett steg.")
        elif schedule_errors:
            st.error(f"Schemat har {len(schedule_errors)} fel och kan inte publiceras. Se schemakontrollen nedan.")
        elif schedule_warnings:
            st.warning("Schemat har varningar. Granska dem och godkänn dem i vänsterspalten före publicering.")
        elif unpublished_total:
            st.warning("Schemat är ett utkast. Kontrollera matchlistan och publicera sedan från vänsterspalten.")
        else:
            st.success("Det aktuella spelschemat är publicerat i Turneringsvyn.")

        st.markdown("**Kontroll per grupp**")
        team_counts = {
            row["group_id"]: row["n"]
            for row in all_rows(
                "SELECT group_id,COUNT(*) AS n FROM teams WHERE tournament_id=? AND group_id IS NOT NULL GROUP BY group_id",
                (tid,),
            )
        }
        match_counts = {
            row["group_id"]: row
            for row in all_rows(
                """SELECT group_id,
                          COUNT(*) AS created_n,
                          SUM(CASE WHEN scheduled_start IS NOT NULL THEN 1 ELSE 0 END) AS scheduled_n,
                          SUM(CASE WHEN schedule_published=1 THEN 1 ELSE 0 END) AS published_n
                   FROM matches
                   WHERE tournament_id=? AND stage='Gruppspel'
                   GROUP BY group_id""",
                (tid,),
            )
        }
        group_status_rows = []
        for group in schedule_groups:
            team_count = int(team_counts.get(group["id"], 0) or 0)
            counts = match_counts.get(group["id"]) or {}
            expected_matches = team_count * (team_count - 1) // 2
            group_status_rows.append({
                "Grupp": group["name"],
                "Lag": team_count,
                "Förväntade möten": expected_matches,
                "Skapade": int(counts.get("created_n", 0) or 0),
                "Schemalagda": int(counts.get("scheduled_n", 0) or 0),
                "Publicerade": int(counts.get("published_n", 0) or 0),
            })
        if group_status_rows:
            render_centered_table(pd.DataFrame(group_status_rows))

    st.subheader("PDF-export")
    st.caption(
        "Skapa ett komplett, utskriftsvänligt PDF-paket med hela schemat samt separata "
        "scheman per grupp, lag, plan, slutspel och domare."
    )
    pdf_matches = all_rows(
        "SELECT * FROM matches WHERE tournament_id=? AND scheduled_start IS NOT NULL "
        "ORDER BY scheduled_start,pitch_number,id",
        (tid,),
    )
    if not pdf_matches:
        st.info("PDF-export blir tillgänglig när det finns ett genererat spelschema.")
    else:
        pdf_key = f"schedule_pdf_bytes_{tid}"
        pdf_fingerprint_key = f"schedule_pdf_fingerprint_{tid}"
        pdf_fingerprint = "|".join(
            f"{m['id']}:{m['scheduled_start']}:{m['pitch_number']}:{m['home_source']}:{m['away_source']}:"
            f"{m['home_score']}:{m['away_score']}:{m['referee_id']}"
            for m in pdf_matches
        )

        if st.button("Skapa komplett schemapaket som PDF", use_container_width=True, key=f"prepare_pdf_{tid}"):
            with st.spinner("CupNavi skapar PDF-paketet…"):
                pdf_teams = all_rows("SELECT * FROM teams WHERE tournament_id=? ORDER BY name", (tid,))
                pdf_groups = all_rows("SELECT * FROM groups WHERE tournament_id=? ORDER BY name", (tid,))
                pdf_refs = all_rows("SELECT * FROM referees WHERE tournament_id=? ORDER BY name", (tid,))

                unique_sources = {
                    source
                    for match_row in pdf_matches
                    for source in (match_row["home_source"], match_row["away_source"])
                    if source
                }
                source_labels_for_pdf = {source: source_label(source) for source in unique_sources}
                source_team_ids_for_pdf = {source: resolve_source(source) for source in unique_sources}

                tournament_for_pdf = {
                    key: tournament[key]
                    for key in ("name", "location", "tournament_date", "start_date", "end_date")
                }
                matches_for_pdf = [
                    {
                        key: match_row[key]
                        for key in (
                            "id", "group_id", "stage", "scheduled_start", "pitch_number",
                            "home_source", "away_source", "home_score", "away_score",
                            "home_penalties", "away_penalties", "referee_id",
                        )
                    }
                    for match_row in pdf_matches
                ]
                teams_for_pdf = [
                    {key: team_row[key] for key in ("id", "name", "group_id")}
                    for team_row in pdf_teams
                ]
                groups_for_pdf = [
                    {key: group_row[key] for key in ("id", "name")}
                    for group_row in pdf_groups
                ]
                refs_for_pdf = [
                    {key: ref_row[key] for key in ("id", "name")}
                    for ref_row in pdf_refs
                ]

                st.session_state[pdf_key] = build_schedule_pdf(
                    tournament_for_pdf,
                    matches_for_pdf,
                    teams_for_pdf,
                    groups_for_pdf,
                    refs_for_pdf,
                    source_labels_for_pdf,
                    source_team_ids_for_pdf,
                )
                st.session_state[pdf_fingerprint_key] = pdf_fingerprint

        if (
            pdf_key in st.session_state
            and st.session_state.get(pdf_fingerprint_key) == pdf_fingerprint
        ):
            safe_pdf_name = re.sub(r"[^A-Za-z0-9_-]+", "_", tournament["name"] or "CupNavi").strip("_")
            st.success("✓ PDF-paketet är klart.")
            st.download_button(
                "Ladda ner alla scheman som PDF",
                data=st.session_state[pdf_key],
                file_name=f"{safe_pdf_name}_alla_scheman.pdf",
                mime="application/pdf",
                use_container_width=True,
                key=f"download_schedule_pdf_{tid}",
            )
        elif pdf_key in st.session_state:
            st.warning("Schemat har ändrats sedan PDF:en skapades. Skapa PDF-paketet på nytt.")

    st.info(
        "Blockerande fel, varningar och lagens vilotider granskas på fliken Kontroller. "
        "Slutspelsmatcher får tid och matchnummer direkt; innan lagen är klara visas platshållare som "
        "Vinnaren i Grupp A eller Vinnare match X."
    )

    travel_teams = all_rows("SELECT * FROM teams WHERE tournament_id=? ORDER BY name", (tid,))
    st.subheader("Reseinformation för lagen")
    render_centered_table(
        pd.DataFrame([
            {
                "Lag": t["name"],
                "Resväg km": t["distance_km"],
                "Senare första match": "Ja" if t["late_first_match"] else "Nej",
                "Första match tidigast": t["earliest_first_time"] or "–",
                "Kommentar": t["travel_note"] or "",
            }
            for t in travel_teams
        ])
    )
    adjustable_matches = all_rows(
        "SELECT * FROM matches WHERE tournament_id=? AND scheduled_start IS NOT NULL ORDER BY scheduled_start,pitch_number,id",
        (tid,),
    )
    if adjustable_matches:
        with st.expander("Dra och släpp matcher mellan befintliga tid/plan-platser", expanded=False):
            st.caption(
                "Dra matcherna till önskad ordning. När du tillämpar ordningen får matcherna "
                "de befintliga tid/plan-platserna uppifrån och ned. Exakta tider och planer kan "
                "fortfarande finjusteras i formuläret under. CupNavi validerar schemat efter ändringen."
            )
            if sort_items is None:
                st.warning(
                    "Drag-and-drop-komponenten kunde inte laddas. Kontrollera att streamlit-sortables "
                    "är installerat från requirements.txt."
                )
            else:
                drag_items = [
                    f"#{row['id']} | {swedish_datetime(row['scheduled_start'])} | Plan {row['pitch_number']} | "
                    f"{source_label(row['home_source'])} – {source_label(row['away_source'])}"
                    for row in adjustable_matches
                ]
                dragged_items = sort_items(
                    drag_items,
                    direction="vertical",
                    custom_style="""
                    .sortable-item {
                        background:#ffffff;
                        color:#172033;
                        border:1px solid #cbd5e1;
                        border-radius:10px;
                        padding:10px 12px;
                        margin:5px 0;
                        font-weight:700;
                    }
                    .sortable-item:hover {
                        background:#f0fdf4;
                        border-color:#86efac;
                    }
                    """,
                )
                original_ids = [row["id"] for row in adjustable_matches]
                dragged_items = dragged_items or drag_items
                dragged_ids = [
                    int(item.split("|", 1)[0].strip().lstrip("#"))
                    for item in dragged_items
                ]
                if dragged_ids != original_ids:
                    st.warning(
                        "Du har ändrat ordningen. Klicka på Tillämpa drag-and-drop-ordningen "
                        "för att spara. Schemat avpubliceras tills kontrollerna är granskade igen."
                    )
                else:
                    st.caption("Ordningen är oförändrad.")

                if st.button(
                    "Tillämpa drag-and-drop-ordningen",
                    type="primary",
                    use_container_width=True,
                    disabled=dragged_ids == original_ids,
                    key=f"apply_drag_schedule_{tid}",
                ):
                    slots = [
                        (row["scheduled_start"], row["pitch_number"])
                        for row in adjustable_matches
                    ]
                    original_by_id = {row["id"]: row for row in adjustable_matches}
                    updates = []
                    for match_id, (slot_start, slot_pitch) in zip(dragged_ids, slots):
                        original = original_by_id[match_id]
                        changed = (
                            original["scheduled_start"] != slot_start
                            or int(original["pitch_number"] or 0) != int(slot_pitch or 0)
                        )
                        updates.append(
                            (
                                slot_start,
                                slot_pitch,
                                1 if changed else int(original["schedule_locked"] or 0),
                                match_id,
                            )
                        )
                    with db() as con:
                        con.executemany(
                            """UPDATE matches
                               SET scheduled_start=?,pitch_number=?,schedule_locked=?,schedule_published=0
                               WHERE id=?""",
                            updates,
                        )
                        con.execute(
                            "UPDATE tournaments SET is_published=0,schedule_dirty=0 WHERE id=?",
                            (tid,),
                        )
                        con.commit()
                    _clear_render_query_cache()
                    post_errors, post_warnings, _ = validate_schedule(tid, tournament, rules)
                    if post_errors:
                        st.session_state["schedule_message"] = (
                            "error",
                            f"Drag-and-drop sparades men gav {len(post_errors)} blockerande schemafel. "
                            "Öppna Kontroller och rätta dem innan publicering.",
                        )
                    elif post_warnings:
                        st.session_state["schedule_message"] = (
                            "warning",
                            f"Drag-and-drop sparades. Schemat har {len(post_warnings)} varningar att granska.",
                        )
                    else:
                        st.session_state["schedule_message"] = (
                            "success",
                            "Drag-and-drop-ordningen sparades och schemakontrollen hittade inga fel.",
                        )
                    st.rerun()

        with st.expander("Justera och lås en match"):
            adjustable_refs = all_rows("SELECT * FROM referees WHERE tournament_id=? ORDER BY name", (tid,))
            adjustable_ids = [match_row["id"] for match_row in adjustable_matches]
            adjust_id = st.selectbox(
                "Match",
                adjustable_ids,
                format_func=lambda match_id: next(
                    f"{match_meta(row)[0]} · {source_label(row['home_source'])}–{source_label(row['away_source'])}"
                    for row in adjustable_matches if row["id"] == match_id
                ),
                key=f"adjust_match_{tid}",
            )
            adjust_match = next(row for row in adjustable_matches if row["id"] == adjust_id)
            adjust_start = datetime.fromisoformat(adjust_match["scheduled_start"])
            with st.form(f"adjust_schedule_{adjust_id}"):
                ad1, ad2, ad3 = st.columns(3)
                adjusted_date = ad1.date_input(
                    "Datum", value=adjust_start.date(),
                    min_value=datetime.fromisoformat(tournament["start_date"] or tournament["tournament_date"]).date(),
                    max_value=datetime.fromisoformat(tournament["end_date"] or tournament["start_date"] or tournament["tournament_date"]).date(),
                )
                adjusted_time = ad2.time_input("Avspark", value=adjust_start.time())
                adjusted_pitch = ad3.number_input("Plan", 1, int(rules["pitch_count"]), int(adjust_match["pitch_number"] or 1))
                referee_options = [None] + [referee["id"] for referee in adjustable_refs]
                referee_index = referee_options.index(adjust_match["referee_id"]) if adjust_match["referee_id"] in referee_options else 0
                adjusted_referee = st.selectbox(
                    "Domare", referee_options, index=referee_index,
                    format_func=lambda referee_id: "Ingen domare" if referee_id is None else next(referee["name"] for referee in adjustable_refs if referee["id"] == referee_id),
                )
                adjusted_locked = st.checkbox(
                    "Lås matchen – automatisk schemaläggning får inte flytta den",
                    value=bool(adjust_match["schedule_locked"]),
                )
                if st.form_submit_button("Spara matchens tid, plan och låsning", type="primary"):
                    adjusted_start = datetime.combine(adjusted_date, adjusted_time).isoformat(timespec="minutes")
                    run(
                        "UPDATE matches SET scheduled_start=?,pitch_number=?,referee_id=?,schedule_locked=?,schedule_published=0 WHERE id=?",
                        (adjusted_start, adjusted_pitch, adjusted_referee, int(adjusted_locked), adjust_id),
                    )
                    run("UPDATE tournaments SET is_published=0 WHERE id=?", (tid,))
                    st.session_state["schedule_message"] = ("success", "Matchen sparades. Kör schemakontrollen och publicera schemat på nytt.")
                    st.rerun()
    st.divider()
    st.subheader("Matchschema")
    refs = all_rows("SELECT * FROM referees WHERE tournament_id=? ORDER BY name", (tid,))
    referee_names = {r["id"]: r["name"] for r in refs}
    scheduled_matches = all_rows("SELECT * FROM matches WHERE tournament_id=? AND scheduled_start IS NOT NULL ORDER BY scheduled_start,pitch_number,id", (tid,))
    if not scheduled_matches:
        st.info("Klicka på Skapa matcher och generera spelschema ovan.")
    else:
        schedule_rows = []
        for index, m in enumerate(scheduled_matches, 1):
            home_id = resolve_source(m["home_source"])
            away_id = resolve_source(m["away_source"])
            home = team(home_id)
            away = team(away_id)
            start_dt = datetime.fromisoformat(m["scheduled_start"])
            event_rows = all_rows(
                """
                SELECT players.name, player_match_stats.* FROM player_match_stats
                JOIN players ON players.id=player_match_stats.player_id
                WHERE player_match_stats.match_id=? ORDER BY players.name
                """,
                (m["id"],),
            )
            goals_text = ", ".join(f"{e['name']} ({e['goals']})" for e in event_rows if e["goals"]) or "–"
            assists_text = ", ".join(f"{e['name']} ({e['assists']})" for e in event_rows if e["assists"]) or "–"
            yellow_text = ", ".join(f"{e['name']} ({e['yellow_cards']})" for e in event_rows if e["yellow_cards"]) or "–"
            red_text = ", ".join(f"{e['name']} ({e['red_cards']})" for e in event_rows if e["red_cards"]) or "–"
            home_kit_color, away_kit_color, away_kit_used = match_kit_colors(home, away)
            if kit_color_conflict(home, away):
                kit_note = f"ℹ Om färgerna upplevs som för lika kan {away['name']} behöva ett extraställ" if away else "ℹ Möjlig färglikhet"
            elif away_kit_used:
                kit_note = f"{away['name']} använder sin andra tröjfärg"
            else:
                kit_note = ""
            schedule_rows.append({
                "match_id": m["id"],
                "Match": index,
                "Fas": m["stage"],
                "Plan": m["pitch_number"],
                "Datum": f"{SWEDISH_WEEKDAYS[start_dt.weekday()]} {start_dt.strftime('%Y-%m-%d')}",
                "Tid": start_dt.strftime("%H:%M"),
                "Hemmalag": home["name"] if home else source_label(m["home_source"]),
                "Hemmafärg": kit_swatch(home, "home") if home else None,
                "Bortalag": away["name"] if away else source_label(m["away_source"]),
                "Bortafärg": kit_swatch(away, "away" if away_kit_used else "home") if away else None,
                "Tröjval": kit_note,
                "Domare": referee_names.get(m["referee_id"], "Ej tillsatt"),
                "Låst": "Ja" if m["schedule_locked"] else "Nej",
                "Hemmamål": m["home_score"],
                "Bortamål": m["away_score"],
                "Målskyttar": goals_text,
                "Assister": assists_text,
                "Varningar": yellow_text,
                "Utvisningar": red_text,
            })
        schedule_df = pd.DataFrame(schedule_rows)

        st.markdown("#### Visuell schemaöversikt")
        st.caption("Problem visas direkt på den match där de behöver åtgärdas.")
        for row in schedule_rows:
            issues = []
            if row["Domare"] == "Ej tillsatt":
                issues.append("Domare saknas")
            if row["Tröjval"].startswith("⚠"):
                issues.append("Möjlig färglikhet")
            if row["Hemmalag"].startswith(("Vinnaren i ", "Vinnare match ", "Förlorare match ")):
                issues.append("Hemmalag ej avgjort")
            if row["Bortalag"].startswith(("Vinnaren i ", "Vinnare match ", "Förlorare match ")):
                issues.append("Bortalag ej avgjort")
            issue_html = "".join(
                f"<span class='cn-issue-pill'>{html.escape(issue)}</span>" for issue in issues
            )
            card_class = "cn-admin-match issue" if issues else "cn-admin-match"
            st.markdown(
                f"""
                <div class="{card_class}">
                  <div><div class="number">#{row['Match']}</div><div class="meta">{html.escape(str(row['Fas']))}</div></div>
                  <div><div class="team">{html.escape(str(row['Hemmalag']))}</div><div class="meta">{html.escape(str(row['Datum']))} · {html.escape(str(row['Tid']))}</div></div>
                  <div><div class="team">{html.escape(str(row['Bortalag']))}</div><div class="meta">Plan {html.escape(str(row['Plan']))}</div></div>
                  <div class="ref-col"><div class="meta">Domare</div><div class="team">{html.escape(str(row['Domare']))}</div>{issue_html}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with st.expander("Redigera resultat i tabell"):
            edited_schedule = st.data_editor(
                schedule_df,
                hide_index=True,
                use_container_width=True,
                disabled=["match_id", "Match", "Fas", "Plan", "Datum", "Tid", "Hemmalag", "Hemmafärg", "Bortalag", "Bortafärg", "Tröjval", "Domare", "Låst", "Målskyttar", "Assister", "Varningar", "Utvisningar"],
                column_order=["Match", "Fas", "Plan", "Datum", "Tid", "Hemmalag", "Hemmafärg", "Hemmamål", "Bortamål", "Bortafärg", "Bortalag", "Tröjval", "Domare", "Låst", "Målskyttar", "Assister", "Varningar", "Utvisningar"],
                column_config={
                    "Hemmamål": st.column_config.NumberColumn(min_value=0, step=1),
                    "Bortamål": st.column_config.NumberColumn(min_value=0, step=1),
                    "Hemmafärg": st.column_config.ImageColumn("Hemmafärg", width="small"),
                    "Bortafärg": st.column_config.ImageColumn("Bortafärg", width="small"),
                },
                key=f"schedule_editor_{tid}",
            )
        if st.button("Spara alla resultat i schemat"):
            with db() as con:
                for _, row in edited_schedule.iterrows():
                    home_score = None if pd.isna(row["Hemmamål"]) else int(row["Hemmamål"])
                    away_score = None if pd.isna(row["Bortamål"]) else int(row["Bortamål"])
                    con.execute("UPDATE matches SET home_score=?,away_score=? WHERE id=?", (home_score, away_score, int(row["match_id"])))
                con.commit()
            st.success("Resultaten sparades.")
        st.caption("Målskyttar, assist, varningar och utvisningar registreras under fliken Matchhändelser och visas därefter automatiskt här.")


if admin_page == "Matcher och resultat":
    st.header("Matcher och resultat")
    st.caption("Registrera och uppdatera matchresultat och domartillsättning.")
    refs = all_rows("SELECT * FROM referees WHERE tournament_id=? ORDER BY name", (tid,))
    st.subheader("Registrera resultat och domare")
    st.caption("Matcherna skapas automatiskt från gruppindelningen och den valda slutspelsmodellen.")
    if "bulk_result_message" in st.session_state:
        st.success(st.session_state.pop("bulk_result_message"), icon="✅")
    matches = all_rows("SELECT * FROM matches WHERE tournament_id=? ORDER BY CASE stage WHEN 'Gruppspel' THEN 0 ELSE 1 END, group_id, bracket_id, round_no, match_no", (tid,))
    if not matches:
        st.info("Inga matcher är skapade.")
    else:
        st.subheader("Hela matchschemat")
        all_match_rows = []
        for m in sorted(
            matches,
            key=lambda row: (
                row["scheduled_start"] is None,
                row["scheduled_start"] or "9999-12-31T23:59",
                row["pitch_number"] or 999,
                row["id"],
            ),
        ):
            schedule_text, referee_name = match_meta(m)
            all_match_rows.append({
                "Match": schedule_text.split(" · ", 1)[0] if m["scheduled_start"] else "Ej schemalagd",
                "Fas": m["stage"],
                "Tid/plan": schedule_text.replace(schedule_text.split(" · ", 1)[0] + " · ", "", 1) if m["scheduled_start"] else "Ej schemalagd",
                "Hemmalag": source_label(m["home_source"]),
                "Bortalag": source_label(m["away_source"]),
                "Domare": referee_name,
            })
        render_centered_table(pd.DataFrame(all_match_rows))
        st.caption(
            "Slutspelsmatcherna visas även innan lagen är klara. Exempel: Vinnaren i Grupp A eller Vinnare match 17."
        )

        playable_matches = [m for m in matches if resolve_source(m["home_source"]) and resolve_source(m["away_source"])]
        unresolved_count = len(matches) - len(playable_matches)
        if unresolved_count:
            st.caption(f"{unresolved_count} kommande slutspelsmatch(er) väntar fortfarande på klara lag och kan inte resultatregistreras ännu.")
        if not playable_matches:
            st.info("Det finns ännu inga matcher med två klara lag.")
        else:
            referee_names = {r["id"]: r["name"] for r in refs}
            referee_ids_by_name = {r["name"]: r["id"] for r in refs}
            referee_options = ["Ej tillsatt"] + [r["name"] for r in refs]
            all_result_teams = all_rows("SELECT id,name FROM teams WHERE tournament_id=? ORDER BY name", (tid,))
            result_team_name_by_id = {row["id"]: row["name"] for row in all_result_teams}
            result_team_id_by_name = {row["name"]: row["id"] for row in all_result_teams}
            decision_options = ["–"] + [row["name"] for row in all_result_teams]
            result_rows = []
            for m in playable_matches:
                schedule_text, _ = match_meta(m)
                result_rows.append({
                    "match_id": m["id"],
                    "Match": schedule_text,
                    "Fas": m["stage"],
                    "Hemmalag": source_label(m["home_source"]),
                    "Hemmamål": m["home_score"],
                    "Bortamål": m["away_score"],
                    "Bortalag": source_label(m["away_source"]),
                    "Hemmastraffar": m["home_penalties"] if m["stage"] != "Gruppspel" else None,
                    "Bortastraffar": m["away_penalties"] if m["stage"] != "Gruppspel" else None,
                    "Avgörande vinnare": result_team_name_by_id.get(m["decided_winner_id"], "–") if m["stage"] != "Gruppspel" else "–",
                    "Domare": referee_names.get(m["referee_id"], "Ej tillsatt"),
                })
            edited_results = st.data_editor(
                pd.DataFrame(result_rows),
                hide_index=True,
                use_container_width=True,
                disabled=["match_id", "Match", "Fas", "Hemmalag", "Bortalag"],
                column_order=["Match", "Fas", "Hemmalag", "Hemmamål", "Bortamål", "Bortalag", "Hemmastraffar", "Bortastraffar", "Avgörande vinnare", "Domare"],
                column_config={
                    "Hemmamål": st.column_config.NumberColumn(min_value=0, max_value=99, step=1),
                    "Bortamål": st.column_config.NumberColumn(min_value=0, max_value=99, step=1),
                    "Hemmastraffar": st.column_config.NumberColumn("Straffar hemma", min_value=0, max_value=99, step=1),
                    "Bortastraffar": st.column_config.NumberColumn("Straffar borta", min_value=0, max_value=99, step=1),
                    "Avgörande vinnare": st.column_config.SelectboxColumn(options=decision_options),
                    "Domare": st.column_config.SelectboxColumn(options=referee_options),
                },
                key=f"bulk_results_{tid}",
            )
            if tournament["playoff_tie_rule"] == "Lottning":
                st.caption("Vid oavgjord slutspelsmatch väljer du vinnaren i kolumnen Avgörande vinnare enligt tävlingsregeln Lottning.")
            elif tournament["playoff_tie_rule"] == "Förlängning + straffar":
                st.caption(f"Vid oavgjort spelas {tournament['extra_time_minutes']} min förlängning och därefter straffar. Registrera straffresultatet vid fortsatt oavgjort.")
            else:
                st.caption("Vid oavgjord slutspelsmatch avgörs matchen med straffar direkt. Registrera straffresultatet.")
            # Resultat sparas automatiskt så snart en komplett ändring finns.
            # Vi jämför editorn mot aktuell databasdata och skriver bara ändrade rader.
            original_match_by_id = {int(match_row["id"]): match_row for match_row in playable_matches}
            auto_updates = []
            auto_messages = []
            auto_errors = []

            for _, row in edited_results.iterrows():
                match_id = int(row["match_id"])
                original_match = original_match_by_id[match_id]

                home_score = None if pd.isna(row["Hemmamål"]) else int(row["Hemmamål"])
                away_score = None if pd.isna(row["Bortamål"]) else int(row["Bortamål"])
                home_penalties = None if pd.isna(row["Hemmastraffar"]) else int(row["Hemmastraffar"])
                away_penalties = None if pd.isna(row["Bortastraffar"]) else int(row["Bortastraffar"])
                referee_id = referee_ids_by_name.get(row["Domare"])

                original_home = original_match["home_score"]
                original_away = original_match["away_score"]
                original_hp = original_match["home_penalties"]
                original_ap = original_match["away_penalties"]
                original_decided = original_match["decided_winner_id"]
                original_referee = original_match["referee_id"]

                row_changed = any([
                    home_score != original_home,
                    away_score != original_away,
                    home_penalties != original_hp,
                    away_penalties != original_ap,
                    referee_id != original_referee,
                    (
                        row["Fas"] != "Gruppspel"
                        and result_team_id_by_name.get(row["Avgörande vinnare"]) != original_decided
                        and row["Avgörande vinnare"] != "–"
                    ),
                ])
                if not row_changed:
                    continue

                # Ett resultat ska aldrig sparas halvt.
                if (home_score is None) != (away_score is None):
                    auto_messages.append(
                        f"{row['Hemmalag']}–{row['Bortalag']}: fyll i båda målresultaten så sparas det automatiskt."
                    )
                    continue

                decided_winner_id = None
                if row["Fas"] == "Gruppspel":
                    home_penalties = None
                    away_penalties = None
                elif home_score is not None and home_score == away_score:
                    home_team_id = result_team_id_by_name.get(row["Hemmalag"])
                    away_team_id = result_team_id_by_name.get(row["Bortalag"])

                    if tournament["playoff_tie_rule"] == "Lottning":
                        selected_winner_id = result_team_id_by_name.get(row["Avgörande vinnare"])
                        home_penalties = None
                        away_penalties = None
                        if selected_winner_id in (home_team_id, away_team_id):
                            decided_winner_id = selected_winner_id
                        else:
                            auto_messages.append(
                                f"{row['Hemmalag']}–{row['Bortalag']}: resultatet sparas, men välj vinnare av lottningen för att avgöra matchen."
                            )
                    else:
                        # Oavgjort resultat får sparas direkt. Straffarna kan fyllas i efteråt.
                        if home_penalties is not None or away_penalties is not None:
                            if (
                                home_penalties is None
                                or away_penalties is None
                                or home_penalties == away_penalties
                            ):
                                auto_errors.append(
                                    f"{row['Hemmalag']}–{row['Bortalag']}: fyll i ett komplett och avgörande straffresultat."
                                )
                                continue
                        else:
                            auto_messages.append(
                                f"{row['Hemmalag']}–{row['Bortalag']}: det oavgjorda resultatet sparas. Ange straffresultat för att avgöra matchen."
                            )
                else:
                    home_penalties = None
                    away_penalties = None

                auto_updates.append(
                    (
                        home_score,
                        away_score,
                        home_penalties,
                        away_penalties,
                        decided_winner_id,
                        referee_id,
                        match_id,
                    )
                )

            for message in auto_errors:
                st.error(message)
            for message in auto_messages:
                st.info(message)

            if auto_updates:
                with db() as con:
                    con.executemany(
                        """UPDATE matches
                           SET home_score=?,away_score=?,home_penalties=?,away_penalties=?,
                               decided_winner_id=?,referee_id=?
                           WHERE id=?""",
                        auto_updates,
                    )
                    con.commit()
                _clear_render_query_cache()
                for home_score, away_score, home_penalties, away_penalties, decided_winner_id, referee_id, changed_match_id in auto_updates:
                    if home_score is None or away_score is None:
                        continue
                    changed_match = original_match_by_id[changed_match_id]
                    description = f"{source_label(changed_match['home_source'])}–{source_label(changed_match['away_source'])} {home_score}–{away_score}"
                    if home_penalties is not None and away_penalties is not None:
                        description += f" ({home_penalties}–{away_penalties} str.)"
                    add_feed_item(tid, f"Slut: {description}", category="Resultat", related_match_id=changed_match_id)
                    for team_id in _match_team_ids(changed_match):
                        add_team_notification(tid, team_id, "Nytt resultat", description,
                                              event_key=f"result:{changed_match_id}:{home_score}:{away_score}:{home_penalties}:{away_penalties}")

                st.session_state["_validation_dirty"] = True
                st.session_state["bulk_result_message"] = "✓ Sparat automatiskt"
                st.rerun()

            st.caption("✓ Resultat och ändringar sparas automatiskt – ingen Spara-knapp behövs.")


if admin_page == "Matchhändelser":
    st.header("Matchhändelser")
    st.caption("Registrera mål, assist, varningar och utvisningar för spelarna i respektive match.")
    st.subheader("Registrera mål, assist, varningar och utvisningar")
    played_matches = all_rows("SELECT * FROM matches WHERE tournament_id=? AND home_score IS NOT NULL AND away_score IS NOT NULL ORDER BY id DESC", (tid,))
    playable_matches = [m for m in played_matches if resolve_source(m["home_source"]) and resolve_source(m["away_source"])]
    if not playable_matches:
        st.info("Spara först ett matchresultat. Därefter kan mål och assist registreras här.")
    else:
        stat_match_id = st.selectbox(
            "Välj match",
            [m["id"] for m in playable_matches],
            format_func=lambda x: match_result_label(next(m for m in playable_matches if m["id"] == x)),
        )
        stat_match = next(m for m in playable_matches if m["id"] == stat_match_id)
        home_team_id = resolve_source(stat_match["home_source"])
        away_team_id = resolve_source(stat_match["away_source"])
        st.caption("Ange spelarens händelser i den valda matchen. Noll innebär ingen notering.")
        for selected_team_id in [home_team_id, away_team_id]:
            selected_team = team(selected_team_id)
            players = all_rows("SELECT * FROM players WHERE team_id=? ORDER BY player_number,name", (selected_team_id,))
            st.markdown(f"#### {selected_team['name']}")
            if not players:
                st.warning("Laget saknar registrerade spelare.")
                continue
            existing = {
                r["player_id"]: r
                for r in all_rows("SELECT * FROM player_match_stats WHERE match_id=? AND player_id IN (SELECT id FROM players WHERE team_id=?)", (stat_match_id, selected_team_id))
            }
            data = pd.DataFrame([
                {
                    "player_id": p["id"],
                    "Nr": p["player_number"],
                    "Spelare": p["name"],
                    "Mål": existing[p["id"]]["goals"] if p["id"] in existing else 0,
                    "Assist": existing[p["id"]]["assists"] if p["id"] in existing else 0,
                    "Varningar": existing[p["id"]]["yellow_cards"] if p["id"] in existing else 0,
                    "Utvisningar": existing[p["id"]]["red_cards"] if p["id"] in existing else 0,
                }
                for p in players
            ])
            edited = st.data_editor(
                data,
                hide_index=True,
                use_container_width=True,
                disabled=["player_id", "Nr", "Spelare"],
                column_order=["Nr", "Spelare", "Mål", "Assist", "Varningar", "Utvisningar"],
                column_config={
                    "Mål": st.column_config.NumberColumn(min_value=0, step=1),
                    "Assist": st.column_config.NumberColumn(min_value=0, step=1),
                    "Varningar": st.column_config.NumberColumn(min_value=0, step=1),
                    "Utvisningar": st.column_config.NumberColumn(min_value=0, step=1),
                },
                key=f"stats_editor_{stat_match_id}_{selected_team_id}",
            )
            team_goals_in_match = int(
                stat_match["home_score"] if selected_team_id == home_team_id else stat_match["away_score"]
            )
            entered_goals = int(edited["Mål"].fillna(0).sum())
            entered_assists = int(edited["Assist"].fillna(0).sum())
            st.caption(
                f"{selected_team['name']} gjorde {team_goals_in_match} mål i matchen. "
                f"Registrerat just nu: {entered_goals} mål och {entered_assists} assist."
            )
            event_validation = validate_match_event_totals(
                team_goals_in_match, entered_goals, entered_assists
            )
            for message in event_validation["errors"]:
                st.error(f"{selected_team['name']}: {message}")

            autosave_message_key = f"event_autosave_message_{stat_match_id}_{selected_team_id}"
            if autosave_message_key in st.session_state:
                st.success(st.session_state.pop(autosave_message_key), icon="✅")

            # Händelser sparas automatiskt när ändringen är giltig.
            # Endast faktiskt ändrade spelarrader skrivs till databasen.
            changed_event_rows = []
            for _, row in edited.iterrows():
                player_id = int(row["player_id"])
                previous = existing.get(player_id)

                goals = int(row["Mål"] or 0)
                assists = int(row["Assist"] or 0)
                yellow_cards = int(row["Varningar"] or 0)
                red_cards = int(row["Utvisningar"] or 0)

                previous_values = (
                    int(previous["goals"] or 0) if previous else 0,
                    int(previous["assists"] or 0) if previous else 0,
                    int(previous["yellow_cards"] or 0) if previous else 0,
                    int(previous["red_cards"] or 0) if previous else 0,
                )
                new_values = (goals, assists, yellow_cards, red_cards)

                if new_values != previous_values:
                    changed_event_rows.append(
                        (stat_match_id, player_id, goals, assists, yellow_cards, red_cards)
                    )

            if changed_event_rows and event_validation["ok"]:
                with db() as con:
                    for match_id, player_id, goals, assists, yellow_cards, red_cards in changed_event_rows:
                        con.execute(
                            """
                            INSERT INTO player_match_stats(match_id,player_id,goals,assists,yellow_cards,red_cards)
                            VALUES(?,?,?,?,?,?)
                            ON CONFLICT(match_id,player_id)
                            DO UPDATE SET goals=excluded.goals, assists=excluded.assists,
                                yellow_cards=excluded.yellow_cards, red_cards=excluded.red_cards
                            """,
                            (match_id, player_id, goals, assists, yellow_cards, red_cards),
                        )
                    con.commit()

                st.session_state[autosave_message_key] = "✓ Sparat automatiskt"
                st.rerun()

            if changed_event_rows and not event_validation["ok"]:
                st.caption("Ändringen sparas automatiskt så snart mål/assist stämmer med matchresultatet.")
            else:
                st.caption("✓ Händelser sparas automatiskt – ingen Spara-knapp behövs.")

            registered_goals = int(edited["Mål"].sum())
            expected_goals = stat_match["home_score"] if selected_team_id == home_team_id else stat_match["away_score"]
            if registered_goals != expected_goals:
                st.warning(f"Registrerade spelarmål: {registered_goals}. Matchresultatet visar {expected_goals} mål. Skillnaden kan exempelvis vara självmål.")


if admin_page == "Besöksstatistik":
    st.header(tr("Besöksstatistik"))
    st.caption(
        "Statistiken gäller den publika turneringsvyn. CupNavi lagrar inte IP-adresser. "
        "Unika besökare avser unika besökssessioner i webbläsaren."
    )

    period_label = st.selectbox(
        tr("Period"),
        [tr("Senaste 7 dagarna"), tr("Senaste 30 dagarna"), tr("Senaste 90 dagarna"), tr("All tid")],
        index=1,
        key=f"visitor_period_{tid}",
    )
    period_days = {
        tr("Senaste 7 dagarna"): 7,
        tr("Senaste 30 dagarna"): 30,
        tr("Senaste 90 dagarna"): 90,
        tr("All tid"): None,
    }[period_label]

    analytics_rows = all_rows(
        """SELECT first_seen,last_seen,view_count,device_type,browser,source
           FROM visitor_sessions
           WHERE tournament_id=?
           ORDER BY first_seen""",
        (tid,),
    )

    now_stats = datetime.now()
    parsed_rows = []
    for row in analytics_rows:
        try:
            first_seen = datetime.fromisoformat(row["first_seen"])
            last_seen = datetime.fromisoformat(row["last_seen"])
        except Exception:
            continue
        if period_days is not None and first_seen < now_stats - timedelta(days=period_days):
            continue
        parsed_rows.append({
            "first_seen": first_seen,
            "last_seen": last_seen,
            "view_count": int(row["view_count"] or 0),
            "device_type": row["device_type"] or "Övrig",
            "browser": row["browser"] or "Övrig",
            "source": row["source"] or "Direkt / okänd",
        })

    if not parsed_rows:
        st.info("Det finns ännu ingen besöksdata för den valda perioden.")
    else:
        unique_sessions = len(parsed_rows)
        total_views = sum(row["view_count"] for row in parsed_rows)
        today = now_stats.date()
        today_rows = [row for row in parsed_rows if row["first_seen"].date() == today]
        today_sessions = len(today_rows)
        today_views = sum(row["view_count"] for row in today_rows)
        active_30m = sum(
            1 for row in parsed_rows
            if row["last_seen"] >= now_stats - timedelta(minutes=30)
        )
        avg_views = total_views / unique_sessions if unique_sessions else 0

        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Unika sessioner", unique_sessions)
        m2.metric("Sidvisningar", total_views)
        m3.metric("Besök idag", today_sessions)
        m4.metric("Sidvisningar idag", today_views)
        m5.metric("Aktiva senaste 30 min", active_30m)
        st.caption(f"Genomsnitt: {avg_views:.1f} sidvisningar per besökssession.")

        # Daily development.
        daily = {}
        for row in parsed_rows:
            day = row["first_seen"].date().isoformat()
            daily.setdefault(day, {"Sessioner": 0, "Sidvisningar": 0})
            daily[day]["Sessioner"] += 1
            daily[day]["Sidvisningar"] += row["view_count"]

        daily_df = pd.DataFrame([
            {"Datum": day, **values}
            for day, values in sorted(daily.items())
        ])
        if not daily_df.empty:
            st.markdown("#### Utveckling över tid")
            chart_df = daily_df.set_index("Datum")[["Sessioner", "Sidvisningar"]]
            st.line_chart(chart_df, use_container_width=True)
            render_centered_table(daily_df)

        breakdown_col1, breakdown_col2, breakdown_col3 = st.columns(3)

        def _breakdown_dataframe(key, label):
            counts = {}
            views = {}
            for row in parsed_rows:
                value = row[key] or "Övrig"
                counts[value] = counts.get(value, 0) + 1
                views[value] = views.get(value, 0) + row["view_count"]
            return pd.DataFrame([
                {
                    label: value,
                    "Sessioner": counts[value],
                    "Sidvisningar": views[value],
                    "Andel": f"{counts[value] / unique_sessions * 100:.0f} %",
                }
                for value in sorted(counts, key=lambda item: (-counts[item], item))
            ])

        with breakdown_col1:
            st.markdown("#### Enheter")
            device_df = _breakdown_dataframe("device_type", "Enhet")
            st.bar_chart(device_df.set_index("Enhet")["Sessioner"], use_container_width=True)
            render_centered_table(device_df)

        with breakdown_col2:
            st.markdown("#### Webbläsare")
            browser_df = _breakdown_dataframe("browser", "Webbläsare")
            st.bar_chart(browser_df.set_index("Webbläsare")["Sessioner"], use_container_width=True)
            render_centered_table(browser_df)

        with breakdown_col3:
            st.markdown("#### Trafikkälla")
            source_df = _breakdown_dataframe("source", "Källa")
            st.bar_chart(source_df.set_index("Källa")["Sessioner"], use_container_width=True)
            render_centered_table(source_df)

        st.markdown("#### Senaste besöken")
        recent_rows = sorted(parsed_rows, key=lambda row: row["last_seen"], reverse=True)[:50]
        recent_df = pd.DataFrame([
            {
                "Första besök": row["first_seen"].strftime("%Y-%m-%d %H:%M"),
                "Senast aktiv": row["last_seen"].strftime("%Y-%m-%d %H:%M"),
                "Sidvisningar": row["view_count"],
                "Enhet": row["device_type"],
                "Webbläsare": row["browser"],
                "Källa": row["source"],
            }
            for row in recent_rows
        ])
        render_centered_table(recent_df)

        st.info(
            "För att skydda besökarnas integritet lagras ingen IP-adress. "
            "En besökssession identifieras med en slumpmässig sessionsnyckel som endast används för statistik."
        )


if admin_page == "Sponsorer":
    st.header("Sponsorer")
    st.caption("Administrera cupens partners. Aktiva sponsorer visas under fliken Partners i turneringsvyn.")

    with st.form(f"new_sponsor_{tid}", clear_on_submit=True):
        st.markdown("#### Lägg till sponsor")
        sc1, sc2 = st.columns(2)
        with sc1:
            sponsor_name = st.text_input("Namn *", placeholder="Exempel: Lokala Banken")
            sponsor_level = st.selectbox("Nivå", ["", "Huvudsponsor", "Guldsponsor", "Silversponsor", "Partner"])
            sponsor_website = st.text_input("Webbplats", placeholder="example.se", help="Du kan skriva example.se eller en fullständig https://-adress.")
        with sc2:
            sponsor_order = st.number_input("Visningsordning", min_value=0, max_value=999, value=0, step=1)
            sponsor_active = st.checkbox("Visa sponsorn publikt direkt", value=True)
            sponsor_logo = st.file_uploader(
                "Logotyp (PNG/JPG/WEBP, max 1,5 MB)",
                type=["png", "jpg", "jpeg", "webp"],
                key=f"new_sponsor_logo_{tid}",
            )
        sponsor_description = st.text_area("Kort beskrivning", max_chars=1000)
        if st.form_submit_button("Lägg till sponsor", type="primary", use_container_width=True):
            if not sponsor_name.strip():
                st.error("Ange sponsorns namn.")
            else:
                try:
                    normalized_website = normalize_website_url(sponsor_website)
                    logo_uri = image_data_uri(sponsor_logo)
                    run(
                        """INSERT INTO sponsors(
                               tournament_id,name,level,description,website_url,
                               logo_data_uri,active,sort_order
                           ) VALUES(?,?,?,?,?,?,?,?)""",
                        (
                            tid, sponsor_name.strip(), sponsor_level or None,
                            sponsor_description.strip() or None,
                            normalized_website, logo_uri,
                            1 if sponsor_active else 0, int(sponsor_order),
                        ),
                    )
                    st.success("✓ Sponsorn är sparad.")
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))

    sponsor_rows = all_rows(
        "SELECT * FROM sponsors WHERE tournament_id=? ORDER BY sort_order,id",
        (tid,),
    )
    st.markdown("#### Befintliga sponsorer")
    if not sponsor_rows:
        st.info("Inga sponsorer har lagts till ännu.")
    else:
        for sponsor in sponsor_rows:
            status = "Publicerad" if sponsor["active"] else "Dold"
            with st.expander(f"{'✓' if sponsor['active'] else '○'} {sponsor['name']} · {status}"):
                with st.form(f"edit_sponsor_{sponsor['id']}"):
                    ec1, ec2 = st.columns(2)
                    with ec1:
                        edit_name = st.text_input("Namn", value=sponsor["name"], key=f"sponsor_name_{sponsor['id']}")
                        levels = ["", "Huvudsponsor", "Guldsponsor", "Silversponsor", "Partner"]
                        current_level = sponsor["level"] or ""
                        edit_level = st.selectbox(
                            "Nivå", levels,
                            index=levels.index(current_level) if current_level in levels else 0,
                            key=f"sponsor_level_{sponsor['id']}",
                        )
                        edit_website = st.text_input("Webbplats", value=sponsor["website_url"] or "", key=f"sponsor_web_{sponsor['id']}")
                    with ec2:
                        edit_order = st.number_input(
                            "Visningsordning", 0, 999, int(sponsor["sort_order"] or 0),
                            key=f"sponsor_order_{sponsor['id']}",
                        )
                        edit_active = st.checkbox(
                            "Visa publikt", value=bool(sponsor["active"]),
                            key=f"sponsor_active_{sponsor['id']}",
                        )
                        replacement_logo = st.file_uploader(
                            "Byt logotyp",
                            type=["png", "jpg", "jpeg", "webp"],
                            key=f"sponsor_logo_{sponsor['id']}",
                        )
                    edit_description = st.text_area(
                        "Kort beskrivning",
                        value=sponsor["description"] or "",
                        max_chars=1000,
                        key=f"sponsor_desc_{sponsor['id']}",
                    )
                    if st.form_submit_button("Spara sponsor", use_container_width=True):
                        if not edit_name.strip():
                            st.error("Namnet får inte vara tomt.")
                        else:
                            try:
                                normalized_website = normalize_website_url(edit_website)
                                edit_logo_uri = sponsor["logo_data_uri"]
                                if replacement_logo is not None:
                                    edit_logo_uri = image_data_uri(replacement_logo)
                                run(
                                    """UPDATE sponsors SET
                                           name=?,level=?,description=?,website_url=?,
                                           logo_data_uri=?,active=?,sort_order=?
                                       WHERE id=? AND tournament_id=?""",
                                    (
                                        edit_name.strip(), edit_level or None,
                                        edit_description.strip() or None,
                                        normalized_website,
                                        edit_logo_uri, 1 if edit_active else 0,
                                        int(edit_order), sponsor["id"], tid,
                                    ),
                                )
                                st.success("✓ Sponsorn är uppdaterad.")
                                st.rerun()
                            except ValueError as exc:
                                st.error(str(exc))
                if st.button("Ta bort sponsor", key=f"delete_sponsor_{sponsor['id']}"):
                    run("DELETE FROM sponsors WHERE id=? AND tournament_id=?", (sponsor["id"], tid))
                    st.rerun()


if admin_page == "Funktionärer":
    st.header("Funktionärer")
    st.caption(
        "Registrera sekretariat, planvärdar, kioskpersonal, sjukvårdare och andra funktionärer. "
        "Du bestämmer själv vilka kontakter som får visas publikt."
    )

    with st.form(f"new_functionary_{tid}", clear_on_submit=True):
        fc1, fc2 = st.columns(2)
        with fc1:
            fn_name = st.text_input("Namn *")
            fn_role = st.selectbox(
                "Roll *",
                ["Sekretariat", "Planvärd", "Tävlingsledning", "Sjukvård", "Kiosk", "Speaker", "Övrigt"],
            )
            fn_pitch = st.number_input("Plan (0 = ingen särskild)", min_value=0, max_value=100, value=0, step=1)
        with fc2:
            fn_phone = st.text_input("Telefon")
            fn_email = st.text_input("E-post")
            fn_public = st.checkbox("Visa kontaktuppgifterna publikt", value=False)
        fn_notes = st.text_area("Anteckning / uppdrag", max_chars=1000)
        if st.form_submit_button("Lägg till funktionär", type="primary", use_container_width=True):
            if not fn_name.strip():
                st.error("Ange ett namn.")
            else:
                run(
                    """INSERT INTO functionaries(
                           tournament_id,name,role,phone,email,pitch_number,notes,public_contact,active
                       ) VALUES(?,?,?,?,?,?,?,?,1)""",
                    (
                        tid, fn_name.strip(), fn_role, fn_phone.strip() or None,
                        fn_email.strip() or None, int(fn_pitch) or None,
                        fn_notes.strip() or None, 1 if fn_public else 0,
                    ),
                )
                st.success("✓ Funktionären är sparad.")
                st.rerun()

    fn_rows = all_rows(
        "SELECT * FROM functionaries WHERE tournament_id=? ORDER BY role,name",
        (tid,),
    )
    if fn_rows:
        render_centered_table(pd.DataFrame([
            {
                "Namn": row["name"],
                "Roll": row["role"],
                "Plan": row["pitch_number"] or "–",
                "Telefon": row["phone"] or "",
                "E-post": row["email"] or "",
                "Publik kontakt": "Ja" if row["public_contact"] else "Nej",
            }
            for row in fn_rows
        ]))
        for row in fn_rows:
            with st.expander(f"{row['role']} · {row['name']}"):
                with st.form(f"edit_functionary_{row['id']}"):
                    e1, e2 = st.columns(2)
                    ename = e1.text_input("Namn", value=row["name"], key=f"fn_name_{row['id']}")
                    roles = ["Sekretariat", "Planvärd", "Tävlingsledning", "Sjukvård", "Kiosk", "Speaker", "Övrigt"]
                    erole = e1.selectbox(
                        "Roll", roles,
                        index=roles.index(row["role"]) if row["role"] in roles else len(roles)-1,
                        key=f"fn_role_{row['id']}",
                    )
                    epitch = e1.number_input(
                        "Plan", min_value=0, max_value=100,
                        value=int(row["pitch_number"] or 0),
                        key=f"fn_pitch_{row['id']}",
                    )
                    ephone = e2.text_input("Telefon", value=row["phone"] or "", key=f"fn_phone_{row['id']}")
                    eemail = e2.text_input("E-post", value=row["email"] or "", key=f"fn_email_{row['id']}")
                    epublic = e2.checkbox(
                        "Visa publikt", value=bool(row["public_contact"]),
                        key=f"fn_public_{row['id']}",
                    )
                    enotes = st.text_area("Anteckning / uppdrag", value=row["notes"] or "", key=f"fn_notes_{row['id']}")
                    if st.form_submit_button("Spara funktionär", use_container_width=True):
                        run(
                            """UPDATE functionaries SET
                                   name=?,role=?,phone=?,email=?,pitch_number=?,notes=?,public_contact=?
                               WHERE id=? AND tournament_id=?""",
                            (
                                ename.strip(), erole, ephone.strip() or None,
                                eemail.strip() or None, int(epitch) or None,
                                enotes.strip() or None, 1 if epublic else 0,
                                row["id"], tid,
                            ),
                        )
                        st.rerun()
                if st.button("Ta bort funktionär", key=f"delete_fn_{row['id']}"):
                    run("DELETE FROM functionaries WHERE id=? AND tournament_id=?", (row["id"], tid))
                    st.rerun()
    else:
        st.info("Inga funktionärer är registrerade ännu.")


if admin_page == "Erbjudanden":
    st.header("Erbjudanden")
    st.caption(
        "Administrera erbjudanden som cupdeltagare och besökare kan använda. "
        "Aktiva erbjudanden visas direkt under fliken Erbjudanden i den publika turneringsvyn."
    )

    with st.form(f"new_offer_{tid}", clear_on_submit=True):
        st.markdown("#### Lägg till erbjudande")
        oc1, oc2 = st.columns(2)
        with oc1:
            offer_title = st.text_input("Rubrik *", placeholder="Exempel: 15 % på hela menyn")
            offer_business = st.text_input("Företag / restaurang", placeholder="Exempel: Restaurang Hörnet")
            offer_code = st.text_input("Rabattkod", placeholder="Exempel: CUPNAVI15")
        with oc2:
            offer_valid = st.text_input("Gäller t.o.m.", placeholder="Exempel: 2026-08-23")
            offer_url = st.text_input("Länk till erbjudandet", placeholder="https://...")
            offer_order = st.number_input("Visningsordning", min_value=0, max_value=999, value=0, step=1)
        offer_description = st.text_area(
            "Beskrivning / villkor",
            placeholder="Exempel: Gäller för cupdeltagare vid uppvisande av deltagarband. Kan ej kombineras med andra erbjudanden.",
            max_chars=1500,
        )
        offer_active = st.checkbox("Visa erbjudandet i turneringsvyn direkt", value=True)
        if st.form_submit_button("Lägg till erbjudande", type="primary", use_container_width=True):
            if not offer_title.strip():
                st.error("Ange en rubrik för erbjudandet.")
            elif offer_url.strip() and not re.match(r"^https?://", offer_url.strip(), re.I):
                st.error("Länken måste börja med http:// eller https://.")
            else:
                run(
                    """INSERT INTO offers(
                           tournament_id,title,business_name,description,discount_code,
                           valid_until,url,active,sort_order
                       ) VALUES(?,?,?,?,?,?,?,?,?)""",
                    (
                        tid,
                        offer_title.strip(),
                        offer_business.strip() or None,
                        offer_description.strip() or None,
                        offer_code.strip() or None,
                        offer_valid.strip() or None,
                        offer_url.strip() or None,
                        1 if offer_active else 0,
                        int(offer_order),
                    ),
                )
                st.success("✓ Erbjudandet är sparat.")
                st.rerun()

    st.markdown("#### Befintliga erbjudanden")
    admin_offers = all_rows(
        "SELECT * FROM offers WHERE tournament_id=? ORDER BY sort_order,id",
        (tid,),
    )
    if not admin_offers:
        st.info("Inga erbjudanden har lagts till ännu.")
    else:
        for offer in admin_offers:
            status = "Publicerat" if offer["active"] else "Dolt"
            with st.expander(f"{'✓' if offer['active'] else '○'} {offer['title']} · {status}"):
                with st.form(f"edit_offer_{offer['id']}"):
                    ec1, ec2 = st.columns(2)
                    with ec1:
                        edit_title = st.text_input("Rubrik", value=offer["title"], key=f"offer_title_{offer['id']}")
                        edit_business = st.text_input("Företag / restaurang", value=offer["business_name"] or "", key=f"offer_business_{offer['id']}")
                        edit_code = st.text_input("Rabattkod", value=offer["discount_code"] or "", key=f"offer_code_{offer['id']}")
                    with ec2:
                        edit_valid = st.text_input("Gäller t.o.m.", value=offer["valid_until"] or "", key=f"offer_valid_{offer['id']}")
                        edit_url = st.text_input("Länk", value=offer["url"] or "", key=f"offer_url_{offer['id']}")
                        edit_order = st.number_input("Visningsordning", 0, 999, int(offer["sort_order"] or 0), key=f"offer_order_{offer['id']}")
                    edit_description = st.text_area("Beskrivning / villkor", value=offer["description"] or "", max_chars=1500, key=f"offer_desc_{offer['id']}")
                    edit_active = st.checkbox("Visa i turneringsvyn", value=bool(offer["active"]), key=f"offer_active_{offer['id']}")
                    if st.form_submit_button("Spara ändringar", use_container_width=True):
                        if not edit_title.strip():
                            st.error("Rubriken får inte vara tom.")
                        elif edit_url.strip() and not re.match(r"^https?://", edit_url.strip(), re.I):
                            st.error("Länken måste börja med http:// eller https://.")
                        else:
                            run(
                                """UPDATE offers SET title=?,business_name=?,description=?,discount_code=?,
                                   valid_until=?,url=?,active=?,sort_order=? WHERE id=? AND tournament_id=?""",
                                (
                                    edit_title.strip(), edit_business.strip() or None,
                                    edit_description.strip() or None, edit_code.strip() or None,
                                    edit_valid.strip() or None, edit_url.strip() or None,
                                    1 if edit_active else 0, int(edit_order), offer["id"], tid,
                                ),
                            )
                            st.success("✓ Ändringarna är sparade.")
                            st.rerun()

                if st.button("Ta bort erbjudande", key=f"delete_offer_{offer['id']}", type="secondary"):
                    st.session_state[f"confirm_delete_offer_{offer['id']}"] = True
                    st.rerun()
                if st.session_state.get(f"confirm_delete_offer_{offer['id']}"):
                    st.warning(f"Ta bort erbjudandet “{offer['title']}”?")
                    dc1, dc2 = st.columns(2)
                    if dc1.button("Ja, ta bort", key=f"confirm_offer_delete_{offer['id']}", type="primary"):
                        run("DELETE FROM offers WHERE id=? AND tournament_id=?", (offer["id"], tid))
                        st.session_state.pop(f"confirm_delete_offer_{offer['id']}", None)
                        st.rerun()
                    if dc2.button("Avbryt", key=f"cancel_offer_delete_{offer['id']}"):
                        st.session_state.pop(f"confirm_delete_offer_{offer['id']}", None)
                        st.rerun()


if admin_page == "Import":
    st.header("Importera lag och trupper")
    st.caption(
        "Ett guidat importflöde: välj typ, ladda upp fil, kontrollera kolumner och fel, "
        "granska resultatet och bekräfta först därefter importen."
    )

    # Stegindikator
    st.markdown(
        """
        <div class="cn-import-steps">
          <div><strong>1</strong><span>Välj typ</span></div>
          <div><strong>2</strong><span>Ladda upp</span></div>
          <div><strong>3</strong><span>Matcha kolumner</span></div>
          <div><strong>4</strong><span>Granska</span></div>
          <div><strong>5</strong><span>Importera</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    import_kind = st.segmented_control(
        "1. Vad vill du importera?",
        ["Lag", "Trupper"],
        default="Lag",
        key=f"import_kind_{tid}",
    )
    if not import_kind:
        import_kind = "Lag"

    with st.expander("📄 Importmallar och format", expanded=False):
        st.write(
            "Du kan använda **CSV eller Excel (.xlsx)**. Kolumnnamnen behöver inte vara exakt som i mallen – "
            "CupNavi försöker känna igen både svenska och engelska rubriker."
        )
        template_col1, template_col2 = st.columns(2)
        team_template = (
            "Lag,Grupp,Hemmafärg,Bortafärg,Resväg km,Senare första match,Första match tidigast,Kommentar\n"
            "Exempellaget,Grupp A,#111827,#FFFFFF,25,Ja,10:00,Reser samma morgon\n"
        ).encode("utf-8-sig")
        squad_template = (
            "Lag,Spelare,Tröjnummer,Födelseår,Position\n"
            "Exempellaget,Anna Andersson,10,2013,Mittfältare\n"
        ).encode("utf-8-sig")
        template_col1.download_button(
            "Ladda ner mall för lag",
            data=team_template,
            file_name="cupnavi_lag_importmall.csv",
            mime="text/csv",
            use_container_width=True,
        )
        template_col2.download_button(
            "Ladda ner mall för trupper",
            data=squad_template,
            file_name="cupnavi_trupp_importmall.csv",
            mime="text/csv",
            use_container_width=True,
        )

    st.markdown("### 2. Ladda upp fil")
    import_file = st.file_uploader(
        "Välj CSV eller XLSX",
        type=["csv", "xlsx"],
        key=f"import_file_{tid}_{import_kind}",
        help="CSV-filer kan använda komma, semikolon eller tab som avgränsare.",
    )

    import_df = None
    import_source_name = None

    if import_file is not None:
        try:
            raw_bytes = import_file.getvalue()
            if import_file.name.lower().endswith(".csv"):
                last_error = None
                for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
                    try:
                        import_df = pd.read_csv(
                            io.BytesIO(raw_bytes),
                            sep=None,
                            engine="python",
                            encoding=encoding,
                        )
                        break
                    except Exception as exc:
                        last_error = exc
                if import_df is None:
                    raise last_error or ValueError("CSV-filen kunde inte läsas.")
                import_source_name = import_file.name
            else:
                excel_file = pd.ExcelFile(io.BytesIO(raw_bytes))
                sheet_name = st.selectbox(
                    "Välj blad i Excel-filen",
                    excel_file.sheet_names,
                    key=f"import_sheet_{tid}_{import_file.name}",
                )
                import_df = pd.read_excel(io.BytesIO(raw_bytes), sheet_name=sheet_name)
                import_source_name = f"{import_file.name} · {sheet_name}"

            import_df = import_df.dropna(how="all").copy()
            import_df.columns = [str(col).strip() for col in import_df.columns]
            import_df = import_df.loc[:, ~import_df.columns.duplicated()].copy()

            if import_df.empty:
                st.error("Filen innehåller inga datarader.")
                import_df = None
            elif len(import_df) > 5000:
                st.error("Filen innehåller fler än 5 000 rader. Dela upp den i mindre filer.")
                import_df = None
            else:
                c1, c2, c3 = st.columns(3)
                c1.metric("Fil", import_file.name)
                c2.metric("Rader", len(import_df))
                c3.metric("Kolumner", len(import_df.columns))
                st.caption(f"Läser: {import_source_name}")
        except Exception as exc:
            st.error(f"Filen kunde inte läsas: {exc}")

    if import_df is not None:
        fields = TEAM_FIELDS if import_kind == "Lag" else PLAYER_FIELDS
        auto_mapping = auto_map_columns(import_df.columns, fields)

        st.markdown("### 3. Matcha kolumner")
        st.caption(
            "CupNavi har försökt matcha kolumnerna automatiskt. Kontrollera särskilt de obligatoriska fälten."
        )

        mapping = {}
        available_options = ["— Använd inte —"] + list(import_df.columns)
        map_cols = st.columns(2)
        for field_index, (field_name, field_spec) in enumerate(fields.items()):
            default_column = auto_mapping.get(field_name)
            default_index = (
                available_options.index(default_column)
                if default_column in available_options
                else 0
            )
            label = f"{field_name}{' *' if field_spec['required'] else ''}"
            selected = map_cols[field_index % 2].selectbox(
                label,
                available_options,
                index=default_index,
                key=f"import_map_{tid}_{import_kind}_{field_name}",
            )
            mapping[field_name] = None if selected == "— Använd inte —" else selected

        missing_required = [
            field for field, spec in fields.items()
            if spec["required"] and not mapping.get(field)
        ]

        if missing_required:
            st.error(
                "Matcha först de obligatoriska fälten: "
                + ", ".join(missing_required)
                + "."
            )
        else:
            existing_team_rows = all_rows(
                "SELECT id,name FROM teams WHERE tournament_id=? ORDER BY name",
                (tid,),
            )
            existing_names = [row["name"] for row in existing_team_rows]

            if import_kind == "Lag":
                max_teams = int(tournament["expected_team_count"] or 0)
                remaining_slots = (
                    max(0, max_teams - len(existing_team_rows))
                    if max_teams > 0 else None
                )
                records, issues = build_team_import_plan(
                    import_df,
                    mapping,
                    existing_names,
                    max_new_teams=remaining_slots,
                )
            else:
                team_lookup = {
                    row["name"].strip().casefold(): row["id"]
                    for row in existing_team_rows
                }
                existing_player_rows = all_rows(
                    """SELECT p.team_id,p.name
                       FROM players p
                       JOIN teams t ON t.id=p.team_id
                       WHERE t.tournament_id=?""",
                    (tid,),
                )
                existing_players = [
                    (row["team_id"], row["name"])
                    for row in existing_player_rows
                ]
                records, issues = build_player_import_plan(
                    import_df,
                    mapping,
                    team_lookup,
                    existing_players,
                )

            error_count = sum(1 for issue in issues if issue["Nivå"] == "Fel")
            skipped_count = sum(1 for issue in issues if issue["Nivå"] == "Hoppa över")

            st.markdown("### 4. Granska")
            s1, s2, s3 = st.columns(3)
            s1.metric("Redo att importera", len(records))
            s2.metric("Hoppar över", skipped_count)
            s3.metric("Fel att rätta", error_count)

            if import_kind == "Lag" and int(tournament["expected_team_count"] or 0) > 0:
                st.caption(
                    f"Turneringen är planerad för maximalt {int(tournament['expected_team_count'])} lag. "
                    f"Nu finns {len(existing_team_rows)} lag."
                )

            if issues:
                issue_df = pd.DataFrame(issues)
                if error_count:
                    st.error(
                        f"{error_count} fel blockerar importen. Rätta filen eller kolumnmappningen och ladda upp igen."
                    )
                elif skipped_count:
                    st.info(
                        f"{skipped_count} rader kommer att hoppas över eftersom de redan finns."
                    )
                st.dataframe(
                    issue_df,
                    use_container_width=True,
                    hide_index=True,
                    height=min(360, 42 + 35 * min(len(issue_df), 9)),
                )
                issue_csv = issue_df.to_csv(index=False).encode("utf-8-sig")
                st.download_button(
                    "Ladda ner felrapport",
                    data=issue_csv,
                    file_name=f"cupnavi_importkontroll_{import_kind.lower()}.csv",
                    mime="text/csv",
                    use_container_width=True,
                )

            if records:
                if import_kind == "Lag":
                    preview_df = pd.DataFrame([
                        {
                            "Lag": row["name"],
                            "Grupp": row["group"] or "–",
                            "Hemmafärg": row["home_color"],
                            "Bortafärg": row["away_color"],
                            "Resväg km": row["distance_km"],
                            "Senare första match": "Ja" if row["late_first_match"] else "Nej",
                            "Första match tidigast": row["earliest_first_time"] or "–",
                        }
                        for row in records[:100]
                    ])
                else:
                    preview_df = pd.DataFrame([
                        {
                            "Lag": row["team_name"],
                            "Spelare": row["player_name"],
                            "Tröjnummer": row["player_number"] if row["player_number"] is not None else "–",
                            "Födelseår": row["birth_year"] if row["birth_year"] is not None else "–",
                            "Position": row["position"] or "–",
                        }
                        for row in records[:100]
                    ])
                with st.expander(
                    f"Förhandsgranska {min(len(records), 100)} av {len(records)} rader",
                    expanded=error_count == 0,
                ):
                    st.dataframe(preview_df, use_container_width=True, hide_index=True)

            st.markdown("### 5. Bekräfta import")
            if error_count:
                st.warning("Importknappen låses tills alla blockerande fel är lösta.")
            elif not records:
                st.info("Det finns inga nya rader att importera.")
            else:
                create_groups = True
                if import_kind == "Lag":
                    create_groups = st.checkbox(
                        "Skapa grupper som finns i filen men inte redan i CupNavi",
                        value=True,
                        key=f"import_create_groups_{tid}",
                    )

                confirmed = st.checkbox(
                    f"Jag har granskat importen och vill lägga till {len(records)} "
                    + ("lag." if import_kind == "Lag" else "spelare."),
                    value=False,
                    key=f"import_confirm_{tid}_{import_kind}_{import_file.name}",
                )

                button_label = "Importera lagen" if import_kind == "Lag" else "Importera trupperna"
                if st.button(
                    button_label,
                    type="primary",
                    use_container_width=True,
                    disabled=not confirmed,
                    key=f"import_execute_{tid}_{import_kind}",
                ):
                    try:
                        con = db()
                        try:
                            if not CLOUD_DATABASE_ENABLED:
                                con.execute("BEGIN IMMEDIATE")

                            if import_kind == "Lag":
                                group_rows = _rows_from_cursor(
                                    con.execute(
                                        "SELECT id,name FROM groups WHERE tournament_id=?",
                                        (tid,),
                                    )
                                )
                                group_map = {
                                    row["name"].strip().casefold(): row["id"]
                                    for row in group_rows
                                }

                                # Re-check max within the write transaction.
                                max_row = _one_from_cursor(
                                    con.execute(
                                        "SELECT COALESCE(expected_team_count,0) AS max_teams FROM tournaments WHERE id=?",
                                        (tid,),
                                    )
                                )
                                count_row = _one_from_cursor(
                                    con.execute(
                                        "SELECT COUNT(*) AS n FROM teams WHERE tournament_id=?",
                                        (tid,),
                                    )
                                )
                                max_teams = int(max_row["max_teams"] or 0)
                                current_count = int(count_row["n"] or 0)
                                if max_teams > 0 and current_count + len(records) > max_teams:
                                    raise TeamLimitReachedError(max_teams)

                                for record in records:
                                    group_id = None
                                    group_name = record["group"]
                                    if group_name:
                                        group_id = group_map.get(group_name.casefold())
                                        if group_id is None and create_groups:
                                            cur = con.execute(
                                                "INSERT INTO groups(tournament_id,name) VALUES(?,?)",
                                                (tid, group_name),
                                            )
                                            group_id = cur.lastrowid
                                            group_map[group_name.casefold()] = group_id

                                    con.execute(
                                        """INSERT INTO teams(
                                               tournament_id,name,group_id,primary_color,secondary_color,
                                               home_pattern,home_color_2,away_pattern,away_color_2,
                                               distance_km,late_first_match,earliest_first_time,travel_note
                                           ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                                        (
                                            tid, record["name"], group_id,
                                            record["home_color"], record["away_color"],
                                            "Helfärgad", "#FFFFFF", "Helfärgad", "#111827",
                                            record["distance_km"], int(record["late_first_match"]),
                                            record["earliest_first_time"], record["comment"] or None,
                                        ),
                                    )
                                con.execute(
                                    "UPDATE tournaments SET schedule_dirty=1,is_published=0 WHERE id=?",
                                    (tid,),
                                )
                            else:
                                for record in records:
                                    con.execute(
                                        """INSERT INTO players(
                                               team_id,player_number,name,birth_year,position
                                           ) VALUES(?,?,?,?,?)""",
                                        (
                                            record["team_id"], record["player_number"],
                                            record["player_name"], record["birth_year"],
                                            record["position"] or None,
                                        ),
                                    )

                            con.commit()
                        except Exception:
                            con.rollback()
                            raise
                        finally:
                            con.close()

                        _clear_render_query_cache()
                        st.session_state["import_success_message"] = (
                            f"✓ Import klar: {len(records)} "
                            + ("lag lades till." if import_kind == "Lag" else "spelare lades till.")
                        )
                        st.rerun()
                    except TeamLimitReachedError as exc:
                        st.error(
                            f"Importen avbröts utan att något lades till eftersom maxantalet "
                            f"{exc.args[0]} lag skulle överskridas."
                        )
                    except Exception as exc:
                        st.error(
                            "Importen kunde inte genomföras. Inga rader ska ha sparats. "
                            f"Teknisk information: {exc}"
                        )

    if "import_success_message" in st.session_state:
        st.success(st.session_state.pop("import_success_message"))


if admin_page == "Cupverktyg":
    st.header("Cupverktyg")
    st.caption("Operativa verktyg för cupdagen: kvalitet, schemaeffekter, förseningar, slutspelsprognos, cupkarta, QR, historik och cupflöde.")

    tool_rules = one_row("SELECT * FROM schedule_rules WHERE tournament_id=?", (tid,))
    tool_teams = all_rows("SELECT * FROM teams WHERE tournament_id=? ORDER BY name", (tid,))
    tool_groups = all_rows("SELECT * FROM groups WHERE tournament_id=? ORDER BY name", (tid,))
    tool_matches = all_rows("SELECT * FROM matches WHERE tournament_id=? ORDER BY scheduled_start,pitch_number,id", (tid,))

    tool_tabs = st.tabs([
        "Kvalitet", "Vad händer om…", "Försening", "Slutspel", "Cupkarta & QR", "Historik", "Cupflöde", "Summering"
    ])

    with tool_tabs[0]:
        schedule_findings = []
        if any(m["scheduled_start"] for m in tool_matches) and tool_rules:
            errors, warnings, _ = validate_schedule(tid, tournament, tool_rules)
            schedule_findings.extend({"severity": "error", "message": message} for message in errors)
            schedule_findings.extend({"severity": "warning", "message": message} for message in warnings)
        quality_score, quality_findings = tournament_quality_score(
            tournament, tool_teams, tool_groups, tool_matches, tool_rules, schedule_findings
        )
        q1, q2, q3 = st.columns(3)
        q1.metric("CupNavi-kvalitet", f"{quality_score}/100")
        q2.metric("Lag/deltagare", len(tool_teams))
        q3.metric("Matcher", len(tool_matches))
        st.progress(quality_score / 100)
        if quality_score >= 90:
            st.success("Cupen ser väl förberedd ut.")
        elif quality_score >= 70:
            st.warning("Cupen är användbar men det finns förbättringspunkter.")
        else:
            st.error("Cupen har flera saker som bör åtgärdas före eller under genomförandet.")
        if quality_findings:
            for finding in quality_findings:
                message = f"−{finding['deduction']} p · {finding['message']}"
                (st.error if finding["severity"] == "error" else st.warning)(message)
        else:
            st.success("Inga kvalitetsavdrag hittades.")

    with tool_tabs[1]:
        st.subheader("🔎 Vad händer om jag flyttar en match?")
        scheduled_for_whatif = [m for m in tool_matches if m["scheduled_start"]]
        if not scheduled_for_whatif:
            st.info("Skapa ett schema först.")
        else:
            whatif_match_id = st.selectbox(
                "Match",
                [m["id"] for m in scheduled_for_whatif],
                format_func=lambda mid: match_result_label(next(m for m in scheduled_for_whatif if m["id"] == mid)),
                key=f"whatif_match_{tid}",
            )
            whatif_match = next(m for m in scheduled_for_whatif if m["id"] == whatif_match_id)
            current_start = datetime.fromisoformat(whatif_match["scheduled_start"])
            wi1, wi2, wi3 = st.columns(3)
            new_date = wi1.date_input("Nytt datum", value=current_start.date(), key=f"wi_date_{tid}")
            new_time = wi2.time_input("Ny tid", value=current_start.time().replace(second=0, microsecond=0), key=f"wi_time_{tid}")
            max_pitch = max([int(m["pitch_number"] or 0) for m in scheduled_for_whatif] + [int(tool_rules["pitch_count"] or 1)])
            new_pitch = wi3.number_input("Ny plan", 1, max(1, max_pitch), int(whatif_match["pitch_number"] or 1), key=f"wi_pitch_{tid}")
            proposed_start = datetime.combine(new_date, new_time)
            impact = analyze_schedule_change(
                tool_matches, whatif_match_id, proposed_start, int(new_pitch), tool_rules,
                resolve_team_id=lambda source: resolve_source(source),
            )
            if impact:
                for item in impact:
                    (st.error if item["severity"] == "error" else st.warning)(item["message"])
            else:
                st.success("Ingen plan-, domar- eller lagvilokrock hittades med de aktuella reglerna.")
            has_errors = any(item["severity"] == "error" for item in impact)
            allow_warning_move = st.checkbox("Jag har granskat eventuella varningar", value=not bool(impact), key=f"wi_accept_{tid}")
            if st.button(
                "Genomför schemaändringen",
                type="primary",
                use_container_width=True,
                key=f"wi_apply_{tid}",
                disabled=has_errors or not allow_warning_move,
            ):
                before = {"scheduled_start": whatif_match["scheduled_start"], "pitch_number": whatif_match["pitch_number"]}
                after = {"scheduled_start": proposed_start.isoformat(timespec="minutes"), "pitch_number": int(new_pitch)}
                run(
                    """UPDATE matches SET original_scheduled_start=COALESCE(original_scheduled_start,scheduled_start),scheduled_start=?,pitch_number=? WHERE id=?""",
                    (after["scheduled_start"], after["pitch_number"], whatif_match_id),
                )
                description = (
                    f"{source_label(whatif_match['home_source'])}–{source_label(whatif_match['away_source'])} "
                    f"flyttad till {swedish_datetime(after['scheduled_start'])}, Plan {after['pitch_number']}"
                )
                record_audit(tid, "schedule_move", "match", description, entity_id=whatif_match_id,
                             before=before, after=after, reversible=True)
                add_feed_item(tid, "Match flyttad", description, category="Schema", related_match_id=whatif_match_id)
                for team_id in _match_team_ids(whatif_match):
                    add_team_notification(tid, team_id, "Matchen har flyttats", description,
                                          event_key=f"move:{whatif_match_id}:{after['scheduled_start']}:{after['pitch_number']}")
                st.success("Ändringen är genomförd och berörda lag får en notis i Min cup.")
                st.rerun()

    with tool_tabs[2]:
        st.subheader("⏱️ Automatisk matchförsening")
        pitch_options = sorted({int(m["pitch_number"]) for m in tool_matches if m["pitch_number"] is not None})
        if not pitch_options:
            st.info("Det finns inga schemalagda planer ännu.")
        else:
            d1, d2 = st.columns(2)
            delay_pitch = d1.selectbox("Plan", pitch_options, format_func=lambda pno: f"Plan {pno}", key=f"delay_pitch_{tid}")
            delay_minutes = d2.number_input("Försening i minuter", 1, 180, 10, key=f"delay_minutes_{tid}")
            pitch_unplayed = [m for m in tool_matches if int(m["pitch_number"] or 0) == delay_pitch and m["home_score"] is None]
            if pitch_unplayed:
                start_options = [m["id"] for m in pitch_unplayed]
                from_match_id = st.selectbox(
                    "Flytta från och med match",
                    start_options,
                    format_func=lambda mid: match_result_label(next(m for m in pitch_unplayed if m["id"] == mid)),
                    key=f"delay_from_{tid}",
                )
                from_match = next(m for m in pitch_unplayed if m["id"] == from_match_id)
                delay_updates = planned_delay_updates(tool_matches, delay_pitch, int(delay_minutes), from_match["scheduled_start"])
                st.caption(f"{len(delay_updates)} ospelade matcher flyttas +{delay_minutes} minuter.")
                if delay_updates:
                    preview = []
                    by_id = {m["id"]: m for m in tool_matches}
                    for match_id, new_start in delay_updates[:12]:
                        old = by_id[match_id]
                        preview.append({
                            "Match": f"{source_label(old['home_source'])} – {source_label(old['away_source'])}",
                            "Från": swedish_datetime(old["scheduled_start"]),
                            "Till": swedish_datetime(new_start),
                        })
                    render_centered_table(pd.DataFrame(preview))
                    if st.button("Tillämpa förseningen", type="primary", use_container_width=True, key=f"delay_apply_{tid}"):
                        before_rows, after_rows = [], []
                        with db() as con:
                            for match_id, new_start in delay_updates:
                                old = by_id[match_id]
                                before_rows.append({"id": match_id, "scheduled_start": old["scheduled_start"]})
                                after_rows.append({"id": match_id, "scheduled_start": new_start})
                                con.execute(
                                    """UPDATE matches SET original_scheduled_start=COALESCE(original_scheduled_start,scheduled_start),scheduled_start=? WHERE id=?""",
                                    (new_start, match_id),
                                )
                            con.commit()
                        _clear_render_query_cache()
                        record_audit(tid, "delay_shift", "pitch", f"Plan {delay_pitch} flyttad +{delay_minutes} min",
                                     entity_id=delay_pitch, before=before_rows, after=after_rows, reversible=True)
                        detail = f"Plan {delay_pitch} ligger cirka {delay_minutes} minuter efter. {len(delay_updates)} matcher har fått nya tider."
                        add_feed_item(tid, f"Plan {delay_pitch} försenad", detail, category="Schema")
                        notified = set()
                        for match_id, new_start in delay_updates:
                            match_row = by_id[match_id]
                            for team_id in _match_team_ids(match_row):
                                key = (team_id, match_id)
                                if key in notified:
                                    continue
                                notified.add(key)
                                add_team_notification(
                                    tid, team_id, "Ny matchtid",
                                    f"{source_label(match_row['home_source'])}–{source_label(match_row['away_source'])}: {swedish_datetime(new_start)} · Plan {delay_pitch}",
                                    event_key=f"delay:{match_id}:{new_start}",
                                )
                        st.rerun()
            else:
                st.info("Det finns inga ospelade matcher på planen.")

    with tool_tabs[3]:
        st.subheader("🔮 Slutspelsprognos")
        forecast_tables = {group["name"]: calculate_table(group["id"], tournament) for group in tool_groups}
        forecast_lines = playoff_preview(forecast_tables, tournament["playoff_format"])
        if forecast_lines:
            st.caption("Detta är en prognos utifrån tabelläget just nu, inte en låst slutspelsseedning.")
            for line in forecast_lines:
                st.write(f"• {line}")
        else:
            st.info("Slutspelsprognos kan visas när grupper och en slutspelsmodell finns.")

    with tool_tabs[4]:
        st.subheader("🗺️ Cupkarta")
        st.caption("Lägg in praktiska punkter. För karta kan du använda en Google Maps-/Apple Maps-/OpenStreetMap-länk till respektive plats.")
        with st.form(f"venue_point_form_{tid}", clear_on_submit=True):
            vp1, vp2 = st.columns(2)
            venue_kind = vp1.selectbox("Typ", ["Plan", "Kiosk", "Toalett", "Parkering", "Sjukvård", "Sekretariat", "Övrigt"])
            venue_label = vp2.text_input("Namn", placeholder="Exempel: Plan 1 eller Huvudparkering")
            venue_detail = st.text_input("Beskrivning", placeholder="Exempel: bakom sporthallen")
            venue_url = st.text_input("Kartlänk (frivillig)", placeholder="https://...")
            if st.form_submit_button("Lägg till punkt", type="primary"):
                if not venue_label.strip():
                    st.error("Ange ett namn.")
                else:
                    try:
                        normalized_venue_url = normalize_website_url(venue_url) if venue_url.strip() else None
                    except ValueError as exc:
                        st.error(str(exc))
                    else:
                        run(
                            "INSERT INTO venue_points(tournament_id,kind,label,detail,url,sort_order) VALUES(?,?,?,?,?,?)",
                            (tid, venue_kind, venue_label.strip(), venue_detail.strip() or None, normalized_venue_url, 0),
                        )
                        record_audit(tid, "venue_add", "venue_point", f"Cupkartpunkt tillagd: {venue_label.strip()}")
                        st.rerun()
        venue_points = all_rows("SELECT * FROM venue_points WHERE tournament_id=? ORDER BY sort_order,id", (tid,))
        if venue_points:
            render_centered_table(pd.DataFrame([
                {"Typ": p["kind"], "Namn": p["label"], "Beskrivning": p["detail"] or "", "Länk": p["url"] or ""}
                for p in venue_points
            ]))
            remove_point_id = st.selectbox("Ta bort punkt", [p["id"] for p in venue_points], format_func=lambda pid: next(p["label"] for p in venue_points if p["id"] == pid), key=f"remove_point_{tid}")
            if st.button("Ta bort vald punkt", key=f"remove_point_button_{tid}"):
                run("DELETE FROM venue_points WHERE id=? AND tournament_id=?", (remove_point_id, tid)); st.rerun()

        st.divider()
        st.subheader("▣ QR-koder per plan")
        pitch_numbers = sorted({int(m["pitch_number"]) for m in tool_matches if m["pitch_number"] is not None})
        if not pitch_numbers:
            st.info("QR-koder per plan skapas när schemat har planer.")
        for pitch_no in pitch_numbers:
            pitch_url = public_cup_url(tid) + f"&pitch={pitch_no}"
            qr_bytes = qr_png_bytes(pitch_url)
            with st.container(border=True):
                c1, c2 = st.columns([1, 2])
                c1.markdown(f"**Plan {pitch_no}**")
                c1.code(pitch_url, language=None)
                if qr_bytes:
                    c2.image(qr_bytes, width=130)
                    c2.download_button(
                        f"Ladda ner QR för Plan {pitch_no}", qr_bytes,
                        file_name=f"cupnavi_plan_{pitch_no}_qr.png", mime="image/png",
                        key=f"pitch_qr_download_{tid}_{pitch_no}",
                    )

    with tool_tabs[5]:
        st.subheader("↩️ Ändringshistorik och ångra")
        audit_rows = all_rows("SELECT * FROM audit_log WHERE tournament_id=? ORDER BY id DESC LIMIT 40", (tid,))
        if not audit_rows:
            st.info("Ingen ny ändringshistorik finns ännu. Historiken registrerar de nya Cupverktygen från och med denna version.")
        for audit in audit_rows:
            with st.container(border=True):
                status = " · ÅNGRAD" if audit["undone_at"] else ""
                st.markdown(f"**{audit['created_at'].replace('T',' ')} · {audit['actor']}**{status}  \\n{audit['description']}")
                can_undo = bool(audit["reversible"]) and not audit["undone_at"] and audit["action_type"] in {"schedule_move", "delay_shift"}
                if can_undo and st.button("Ångra denna ändring", key=f"undo_audit_{audit['id']}"):
                    before = json.loads(audit["before_json"] or "null")
                    if audit["action_type"] == "schedule_move" and isinstance(before, dict):
                        run("UPDATE matches SET scheduled_start=?,pitch_number=? WHERE id=?", (before.get("scheduled_start"), before.get("pitch_number"), audit["entity_id"]))
                    elif audit["action_type"] == "delay_shift" and isinstance(before, list):
                        with db() as con:
                            for item in before:
                                con.execute("UPDATE matches SET scheduled_start=? WHERE id=?", (item.get("scheduled_start"), item.get("id")))
                            con.commit()
                        _clear_render_query_cache()
                    run("UPDATE audit_log SET undone_at=? WHERE id=?", (datetime.now().isoformat(timespec="seconds"), audit["id"]))
                    record_audit(tid, "undo", audit["entity_type"], f"Ångrade: {audit['description']}", entity_id=audit["entity_id"], actor="Admin")
                    st.rerun()

    with tool_tabs[6]:
        st.subheader("📣 Publikt cupflöde")
        with st.form(f"feed_form_{tid}", clear_on_submit=True):
            feed_title = st.text_input("Rubrik", placeholder="Exempel: Plan 2 är cirka 10 minuter sen")
            feed_detail = st.text_area("Detalj (frivillig)")
            feed_category = st.selectbox("Kategori", ["Info", "Schema", "Resultat", "Cup"])
            if st.form_submit_button("Publicera i cupflödet", type="primary"):
                if not feed_title.strip():
                    st.error("Ange en rubrik.")
                else:
                    add_feed_item(tid, feed_title.strip(), feed_detail.strip() or None, category=feed_category, public=True)
                    record_audit(tid, "feed_post", "feed", f"Publicerade i cupflödet: {feed_title.strip()}")
                    st.rerun()
        feed_admin_rows = all_rows("SELECT * FROM cup_feed WHERE tournament_id=? ORDER BY id DESC LIMIT 20", (tid,))
        for item in feed_admin_rows:
            st.markdown(f"**{item['created_at'].replace('T',' ')} · {item['title']}**")
            if item["detail"]:
                st.caption(item["detail"])

    with tool_tabs[7]:
        st.subheader("🏁 Automatisk cupsummering")
        top_scorer_row = one_row(
            """SELECT players.name AS player_name,teams.name AS team_name,SUM(s.goals) AS goals
               FROM player_match_stats s JOIN players ON players.id=s.player_id
               JOIN teams ON teams.id=players.team_id JOIN matches ON matches.id=s.match_id
               WHERE matches.tournament_id=? GROUP BY players.id,players.name,teams.name
               ORDER BY goals DESC,player_name LIMIT 1""",
            (tid,),
        )
        summary = cup_summary(tournament, tool_teams, tool_matches, top_scorer_row)
        score_word = sport_profile(summary["sport"])["score_label"]
        summary_lines = [
            f"# {summary['name']}",
            f"Sport: {summary['sport']}",
            f"Lag/deltagare: {summary['teams']}",
            f"Matcher: {summary['played_matches']} spelade av {summary['matches']}",
            f"Totalt registrerade {score_word}: {summary['total_score']}",
        ]
        if summary.get("top_scorer") and summary.get("top_scorer_score", 0) > 0:
            summary_lines.append(f"Toppscorer: {summary['top_scorer']} ({summary['top_scorer_team']}) – {summary['top_scorer_score']}")
        summary_text = "\n".join(summary_lines)
        st.markdown(summary_text)
        st.download_button(
            "Ladda ner cupsummering", summary_text.encode("utf-8"),
            file_name=f"cupnavi_summering_{tid}.md", mime="text/markdown", key=f"summary_download_{tid}"
        )


if admin_page == "Tabeller":
    st.header("Tabeller")
    st.caption("Här visas grupptabellerna automatiskt utifrån registrerade matchresultat.")
    groups = all_rows("SELECT * FROM groups WHERE tournament_id=? ORDER BY name", (tid,))
    if not groups:
        st.info("Skapa minst en grupp.")
    for g in groups:
        st.subheader(g["name"])
        table = calculate_table(g["id"], tournament)
        render_group_table(table, tournament)
        if tournament["table_tiebreak"] == "Inbördes möten först":
            st.caption("Sortering: poäng, inbördes möten, därefter målskillnad och gjorda mål.")
        else:
            st.caption("Sortering: poäng, målskillnad, gjorda mål, därefter lagnamn.")


if admin_page == "Skytteligor":
    st.header("Skytteligor")
    st.caption("Här visas skytteliga, assistliga och kortstatistik utifrån registrerade matchhändelser.")
    st.subheader(tr("Skytteliga"))
    leaders = all_rows(
        """
        SELECT players.name AS player_name, teams.name AS team_name,
               SUM(player_match_stats.goals) AS goals,
               SUM(player_match_stats.assists) AS assists,
               SUM(player_match_stats.yellow_cards) AS yellow_cards,
               SUM(player_match_stats.red_cards) AS red_cards
        FROM player_match_stats
        JOIN players ON players.id=player_match_stats.player_id
        JOIN teams ON teams.id=players.team_id
        JOIN matches ON matches.id=player_match_stats.match_id
        WHERE matches.tournament_id=?
        GROUP BY players.id, players.name, teams.name
        HAVING goals > 0 OR assists > 0 OR yellow_cards > 0 OR red_cards > 0
        """,
        (tid,),
    )
    goal_rows = [
        r for r in sorted(leaders, key=lambda r: (-r["goals"], -r["assists"], r["player_name"].lower()))
        if int(r["goals"] or 0) > 0
    ]
    if goal_rows:
        render_centered_table(pd.DataFrame([{"Pl": i, "Spelare": r["player_name"], "Lag": r["team_name"], "Mål": r["goals"]} for i, r in enumerate(goal_rows, 1)]))
    else:
        st.info("Inga målskyttar har registrerats.")
    st.subheader(tr("Assistliga"))
    assist_rows = [
        r for r in sorted(leaders, key=lambda r: (-r["assists"], -r["goals"], r["player_name"].lower()))
        if int(r["assists"] or 0) > 0
    ]
    if assist_rows:
        render_centered_table(pd.DataFrame([{"Pl": i, "Spelare": r["player_name"], "Lag": r["team_name"], "Assist": r["assists"]} for i, r in enumerate(assist_rows, 1)]))
    else:
        st.info("Inga assist har registrerats.")
    st.subheader("Varningar och utvisningar")
    card_rows = sorted(leaders, key=lambda r: (-r["red_cards"], -r["yellow_cards"], r["player_name"].lower()))
    card_rows = [r for r in card_rows if r["yellow_cards"] or r["red_cards"]]
    if card_rows:
        render_centered_table(pd.DataFrame([{"Spelare": r["player_name"], "Lag": r["team_name"], "Varningar": r["yellow_cards"], "Utvisningar": r["red_cards"]} for r in card_rows]))
    else:
        st.info("Inga varningar eller utvisningar har registrerats.")


if admin_page == "Slutspel":
    st.header("Slutspel")
    st.caption("Slutspelet skapas automatiskt när hela spelschemat genereras under Schema.")

    if not tournament["playoff_model_confirmed"]:
        st.warning("Välj och spara först slutspelsmodell på Adminöversikten.")
    elif tournament["playoff_format"] == "Inget slutspel":
        st.info("Den valda modellen är Inget slutspel.")
    else:
        st.info(
            f"Vald modell: **{tournament['playoff_format']}**. "
            "Det finns ingen separat genereringsknapp – ändra modellen på Adminöversikten och regenerera därefter schemat."
        )

    specs, setup_error = playoff_specs_for_tournament(tid, tournament)
    if setup_error:
        st.error(setup_error)

    brackets, duplicate_brackets = brackets_for_display(tid)
    if duplicate_brackets:
        st.warning("Äldre dubbletter av slutspel finns i databasen. Regenerera hela schemat för att bygga om träden rent.")

    if not brackets:
        if tournament["playoff_format"] != "Inget slutspel":
            st.info("Inga slutspelsmatcher är skapade ännu. Gå till Schema och generera hela spelschemat.")
    else:
        for bracket in brackets:
            st.subheader(bracket["name"])
            bracket_matches = all_rows(
                "SELECT * FROM matches WHERE bracket_id=? ORDER BY round_no,match_no",
                (bracket["id"],),
            )
            if bracket_matches:
                overview_rows = []
                for match_row in bracket_matches:
                    schedule_text, _ = match_meta(match_row)
                    match_number = schedule_text.split(" · ", 1)[0] if match_row["scheduled_start"] else "Ej schemalagd"
                    overview_rows.append({
                        "Match": match_number,
                        "Fas": match_row["stage"],
                        "Hemmalag": source_label(match_row["home_source"]),
                        "Bortalag": source_label(match_row["away_source"]),
                    })
                render_centered_table(pd.DataFrame(overview_rows))
            render_bracket_tree(bracket["id"], public=False)

