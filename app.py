import sqlite3
import html
import base64
import json
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd
import streamlit as st

try:
    from streamlit_sortables import sort_items
except ImportError:
    sort_items = None


st.set_page_config(page_title="Fotbollsturnering", page_icon="⚽", layout="wide")
DB_FILE = Path(__file__).with_name("turnering.db")


def db():
    con = sqlite3.connect(DB_FILE)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def columns(table):
    with db() as con:
        return {row["name"] for row in con.execute(f"PRAGMA table_info({table})")}


def init_db():
    with db() as con:
        con.executescript(
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
                public_information TEXT
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
                schedule_locked INTEGER NOT NULL DEFAULT 0
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
        if "distance_km" not in team_cols:
            con.execute("ALTER TABLE teams ADD COLUMN distance_km INTEGER NOT NULL DEFAULT 0")
        if "late_first_match" not in team_cols:
            con.execute("ALTER TABLE teams ADD COLUMN late_first_match INTEGER NOT NULL DEFAULT 0")
        if "earliest_first_time" not in team_cols:
            con.execute("ALTER TABLE teams ADD COLUMN earliest_first_time TEXT")
        if "travel_note" not in team_cols:
            con.execute("ALTER TABLE teams ADD COLUMN travel_note TEXT")
        con.execute("UPDATE teams SET late_first_match=0, earliest_first_time=NULL")
        if "scheduled_start" not in match_cols:
            con.execute("ALTER TABLE matches ADD COLUMN scheduled_start TEXT")
        if "pitch_number" not in match_cols:
            con.execute("ALTER TABLE matches ADD COLUMN pitch_number INTEGER")
        if "schedule_published" not in match_cols:
            con.execute("ALTER TABLE matches ADD COLUMN schedule_published INTEGER NOT NULL DEFAULT 0")
        if "schedule_locked" not in match_cols:
            con.execute("ALTER TABLE matches ADD COLUMN schedule_locked INTEGER NOT NULL DEFAULT 0")
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


def all_rows(sql, params=()):
    with db() as con:
        return con.execute(sql, params).fetchall()


def one_row(sql, params=()):
    with db() as con:
        return con.execute(sql, params).fetchone()


def run(sql, params=()):
    with db() as con:
        cur = con.execute(sql, params)
        con.commit()
        return cur.lastrowid


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
        hs, aas = m["home_score"], m["away_score"]
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
    for s in stats.values():
        s["MS"] = s["GM"] - s["IM"]
    ordered = sorted(stats.items(), key=lambda x: (-x[1]["P"], -x[1]["MS"], -x[1]["GM"], x[1]["Lag"].lower()))
    return [(team_id, data) for team_id, data in ordered]


def result_winner(match_row, want_loser=False):
    home_id = resolve_source(match_row["home_source"])
    away_id = resolve_source(match_row["away_source"])
    if not home_id or not away_id or match_row["home_score"] is None or match_row["away_score"] is None:
        return None
    hs, aas = match_row["home_score"], match_row["away_score"]
    if hs == aas:
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
        return f"{parts[2]}:an i {group['name']}" if group else "Gruppplacering"
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


def color_swatch(color):
    """Skapa en liten enfärgad tröjfärgsruta för schematabellen."""
    svg = f"""<svg xmlns='http://www.w3.org/2000/svg' width='58' height='24' viewBox='0 0 58 24'>
    <rect x='1' y='1' width='56' height='22' rx='4' fill='{color}' stroke='#475569'/></svg>"""
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("ascii")


def match_kit_colors(home_team, away_team):
    """Välj hemmafärg och byt automatiskt bortalaget till bortafärg vid färgkrock."""
    if not home_team or not away_team:
        return "#9CA3AF", "#FFFFFF", False
    home_color = home_team["primary_color"]
    away_primary = away_team["primary_color"]
    use_away_kit = home_color.strip().casefold() == away_primary.strip().casefold()
    away_color = away_team["secondary_color"] if use_away_kit else away_primary
    return home_color, away_color, use_away_kit


def kit_color_conflict(home_team, away_team):
    """Kontrollera om färgerna fortfarande krockar efter ett automatiskt byte av bortalaget."""
    if not home_team or not away_team:
        return False
    home_color, away_color, _ = match_kit_colors(home_team, away_team)
    return home_color.strip().casefold() == away_color.strip().casefold()


def centered_table(dataframe):
    """Centrera både rubriker och innehåll i färdiga resultat-/serietabeller."""
    return dataframe.style.set_properties(**{"text-align": "center"}).set_table_styles([
        {"selector": "th", "props": [("text-align", "center")]},
        {"selector": "td", "props": [("text-align", "center")]},
    ])


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
    return created


def create_all_group_matches(tournament_id):
    """Skapa alla saknade enkelmöten i samtliga grupper utan dubbletter."""
    groups = all_rows("SELECT id,name FROM groups WHERE tournament_id=? ORDER BY name", (tournament_id,))
    created = 0
    ready_groups = 0
    skipped_groups = []
    for group in groups:
        team_count = one_row("SELECT COUNT(*) AS n FROM teams WHERE group_id=?", (group["id"],))["n"]
        if team_count < 2:
            skipped_groups.append(group["name"])
            continue
        ready_groups += 1
        created += create_round_robin(tournament_id, group["id"])
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


def generate_schedule(tournament_id, tournament, rules, preserve_existing=False):
    try:
        cup_start_date = tournament["start_date"] or tournament["tournament_date"]
        cup_end_date = tournament["end_date"] or cup_start_date
        start = datetime.fromisoformat(f"{cup_start_date}T{rules['first_match_time']}")
        end_date = datetime.fromisoformat(cup_end_date).date()
        latest_kickoff = datetime.strptime(rules["latest_kickoff_time"], "%H:%M").time()
    except (TypeError, ValueError):
        return 0, 0, "Turneringen måste ha giltiga cupdatum, första avspark och senaste avspark."

    def valid_daily_start(candidate):
        if candidate.time() > latest_kickoff:
            candidate = datetime.combine(candidate.date() + timedelta(days=1), start.time())
        return candidate if candidate.date() <= end_date else None
    if not preserve_existing:
        run("UPDATE tournaments SET is_published=0 WHERE id=?", (tournament_id,))
        run("UPDATE matches SET schedule_published=0 WHERE tournament_id=?", (tournament_id,))
        run("UPDATE matches SET scheduled_start=NULL,pitch_number=NULL WHERE tournament_id=? AND schedule_locked=0", (tournament_id,))
    duration = timedelta(
        minutes=(rules["halves"] * rules["minutes_per_half"])
        + ((rules["halves"] - 1) * rules["halftime_minutes"])
    )
    pitch_gap = timedelta(minutes=rules["pitch_break_minutes"])
    avoid_consecutive = bool(rules["avoid_consecutive_matches"])
    consecutive_break = timedelta(minutes=rules["consecutive_match_break_minutes"] if avoid_consecutive else 0)
    pitch_ready = {pitch: start for pitch in range(1, rules["pitch_count"] + 1)}
    team_ready = {}
    team_last_end = {}
    referees = all_rows("SELECT id FROM referees WHERE tournament_id=? ORDER BY name", (tournament_id,))
    referee_ready = {r["id"]: start for r in referees}
    matches = all_rows(
        """
        SELECT * FROM matches WHERE tournament_id=?
        ORDER BY CASE stage
            WHEN 'Gruppspel' THEN 1 WHEN 'Kvartsfinal' THEN 2
            WHEN 'Semifinal' THEN 3 WHEN 'Bronsmatch' THEN 4 WHEN 'Final' THEN 5 ELSE 6 END,
            group_id, bracket_id, round_no, match_no
        """,
        (tournament_id,),
    )
    locked_events = []
    if preserve_existing:
        for existing_match in matches:
            if not existing_match["scheduled_start"] or not existing_match["pitch_number"]:
                continue
            home_id = resolve_source(existing_match["home_source"])
            away_id = resolve_source(existing_match["away_source"])
            if not home_id or not away_id:
                continue
            existing_start = datetime.fromisoformat(existing_match["scheduled_start"])
            existing_end = existing_start + duration
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
            locked_home = resolve_source(locked_match["home_source"])
            locked_away = resolve_source(locked_match["away_source"])
            locked_start = datetime.fromisoformat(locked_match["scheduled_start"])
            locked_events.append({
                "start": locked_start, "end": locked_start + duration, "pitch": locked_match["pitch_number"],
                "referee": locked_match["referee_id"], "teams": {locked_home, locked_away} - {None},
            })

    def move_past_locked(candidate_start, pitch, referee_id, home_id, away_id):
        candidate_teams = {home_id, away_id}
        changed = True
        while changed:
            changed = False
            candidate_end = candidate_start + duration
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
    for match_row in matches:
        if match_row["scheduled_start"] and (preserve_existing or match_row["schedule_locked"]):
            continue
        home_id = resolve_source(match_row["home_source"])
        away_id = resolve_source(match_row["away_source"])
        if not home_id or not away_id:
            unresolved += 1
            continue
        remaining.append((match_row, home_id, away_id))
    last_scheduled_teams = set()
    forced_consecutive = 0
    while remaining:
        candidates = []
        for order, (match_row, home_id, away_id) in enumerate(remaining):
            for pitch in pitch_ready:
                consecutive_penalty = int(avoid_consecutive and bool({home_id, away_id} & last_scheduled_teams))
                basic_start = max(pitch_ready[pitch], team_ready.get(home_id, start), team_ready.get(away_id, start))
                if consecutive_penalty:
                    basic_start = max(
                        basic_start,
                        team_last_end.get(home_id, start) + consecutive_break,
                        team_last_end.get(away_id, start) + consecutive_break,
                    )
                if rules["referee_mode"] == "Automatisk" and referees:
                    for referee in referees:
                        referee_id = referee["id"]
                        candidate_start = valid_daily_start(max(basic_start, referee_ready[referee_id]))
                        candidate_start = move_past_locked(candidate_start, pitch, referee_id, home_id, away_id) if candidate_start else None
                        if candidate_start:
                            candidates.append((candidate_start, consecutive_penalty, order, pitch, referee_id))
                else:
                    candidate_start = valid_daily_start(basic_start)
                    candidate_start = move_past_locked(candidate_start, pitch, match_row["referee_id"], home_id, away_id) if candidate_start else None
                    if candidate_start:
                        candidates.append((candidate_start, consecutive_penalty, order, pitch, match_row["referee_id"]))
        if not candidates:
            unresolved += len(remaining)
            warning = "Alla matcher fick inte plats inom cupens datumintervall och tillåtna avsparkstider."
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
        match_end = match_start + duration
        run(
            "UPDATE matches SET scheduled_start=?,pitch_number=?,referee_id=? WHERE id=?",
            (match_start.isoformat(timespec="minutes"), pitch, referee_id, match_row["id"]),
        )
        pitch_ready[pitch] = match_end + pitch_gap
        team_ready[home_id] = match_end + consecutive_break
        team_ready[away_id] = match_end + consecutive_break
        team_last_end[home_id] = match_end
        team_last_end[away_id] = match_end
        if referee_id and rules["referee_mode"] == "Automatisk":
            referee_ready[referee_id] = match_end + pitch_gap
        scheduled += 1
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
    return scheduled, unresolved, warning


def validate_schedule(tournament_id, tournament, rules):
    """Kontrollera schemat och sammanställ väntetid och belastning per lag."""
    rows = all_rows(
        "SELECT * FROM matches WHERE tournament_id=? AND scheduled_start IS NOT NULL ORDER BY scheduled_start,pitch_number,id",
        (tournament_id,),
    )
    duration = timedelta(minutes=(rules["halves"] * rules["minutes_per_half"]) + ((rules["halves"] - 1) * rules["halftime_minutes"]))
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
        home_id, away_id = resolve_source(match_row["home_source"]), resolve_source(match_row["away_source"])
        home_team, away_team = team(home_id), team(away_id)
        events.append({"number": number, "row": match_row, "start": start_at, "end": start_at + duration, "teams": {home_id, away_id} - {None}})
        if not cup_start <= start_at.date() <= cup_end:
            errors.append(f"Match {number} ligger utanför cupens datumintervall.")
        if start_at.time() < first_time or start_at.time() > latest_time:
            errors.append(f"Match {number} har avspark {start_at.strftime('%H:%M')} utanför tillåten tid.")
        if not match_row["pitch_number"] or not 1 <= match_row["pitch_number"] <= rules["pitch_count"]:
            errors.append(f"Match {number} har en ogiltig plan.")
        if rules["referee_mode"] == "Automatisk" and not match_row["referee_id"]:
            warnings.append(f"Match {number} saknar domare.")
        if kit_color_conflict(home_team, away_team):
            warnings.append(
                f"Färgkrock i match {number}: {away_team['name']} har samma färg som hemmalaget även på sin andra tröja. "
                f"En ytterligare avvikande tröjfärg behöver användas."
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
            elif match_row["home_penalties"] is not None and match_row["away_penalties"] is not None:
                home_winner = match_row["home_penalties"] > match_row["away_penalties"]
                away_winner = match_row["away_penalties"] > match_row["home_penalties"]
        if public and not match_row["schedule_published"]:
            schedule_text, referee = "Tid och plan ej publicerade", "Ej publicerad"
        else:
            schedule_text, referee = match_meta(match_row)
        penalties = ""
        if match_row["home_penalties"] is not None:
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


def render_public_view(tournament_id, tournament):
    st.header("Turneringsöversikt")
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
    schedule, tables, statistics, playoffs, information = st.tabs(
        ["Spelschema", "Tabeller", "Topplistor", "Slutspel", "Information"]
    )
    with schedule:
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
              .public-match-card .color-conflict { color:#9a3412 !important; }
            </style>
            """,
            unsafe_allow_html=True,
        )
        matches = all_rows("SELECT * FROM matches WHERE tournament_id=? AND scheduled_start IS NOT NULL AND schedule_published=1 ORDER BY scheduled_start,pitch_number,id", (tournament_id,))
        referees = {r["id"]: r["name"] for r in all_rows("SELECT * FROM referees WHERE tournament_id=?", (tournament_id,))}
        weather_forecast, weather_status = fetch_weather_forecast(tournament["location"] or "")
        if not matches:
            draft_count = one_row(
                "SELECT COUNT(*) AS n FROM matches WHERE tournament_id=? AND scheduled_start IS NOT NULL AND schedule_published=0",
                (tournament_id,),
            )["n"]
            if draft_count:
                st.info(f"Spelschemat är framtaget men väntar på administratörens godkännande ({draft_count} matcher i utkast).")
            else:
                st.info("Inga matcher har schemalagts och publicerats ännu.")
        for number, match_row in enumerate(matches, 1):
            home = team(resolve_source(match_row["home_source"]))
            away = team(resolve_source(match_row["away_source"]))
            home_name = home["name"] if home else source_label(match_row["home_source"])
            away_name = away["name"] if away else source_label(match_row["away_source"])
            start = swedish_datetime(match_row["scheduled_start"])
            match_weather = weather_for_match(weather_forecast, match_row["scheduled_start"])
            weather_text = weather_label(match_weather) if weather_forecast else weather_status
            score = "Ej spelad" if match_row["home_score"] is None else f"{match_row['home_score']}–{match_row['away_score']}"
            if match_row["home_penalties"] is not None:
                score += f" ({match_row['home_penalties']}–{match_row['away_penalties']} str.)"
            home_primary, away_match_color, away_kit_used = match_kit_colors(home, away)
            color_conflict_html = ""
            if kit_color_conflict(home, away):
                color_conflict_html = (
                    f"<div style='margin-top:10px;padding:7px 10px;border-radius:7px;background:#fff7ed;border:1px solid #fb923c;"
                    f"color:#9a3412;font-size:12px;font-weight:700'>⚠ Färgkrock: även {html.escape(away_name)}s andra tröjfärg krockar. Ett ytterligare avvikande ställ krävs.</div>"
                )
            elif away_kit_used:
                color_conflict_html = (
                    f"<div style='margin-top:10px;padding:7px 10px;border-radius:7px;background:#eff6ff;border:1px solid #93c5fd;"
                    f"color:#1e3a8a;font-size:12px;font-weight:700'>{html.escape(away_name)} använder sin andra tröjfärg på grund av färgkrock.</div>"
                )
            st.markdown(
                f"""
                <div class="public-match-card" style="border:1px solid #d1d5db;border-radius:14px;padding:16px;margin:12px 0;background:linear-gradient(135deg,#ffffff,#f3f6fb);color:#172033;box-shadow:0 4px 12px rgba(15,23,42,.08)">
                  <div style="display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #e5e7eb;padding-bottom:9px">
                    <span class="match-stage" style="font-size:12px;font-weight:700;color:#fff;background:#166534;padding:4px 9px;border-radius:999px">{match_row['stage']}</span>
                    <span class="match-meta" style="font-size:13px;color:#334155">Match {number} · <b>{start}</b> · Plan {match_row['pitch_number']}</span>
                  </div>
                  <div style="display:grid;grid-template-columns:1fr auto 1fr;gap:15px;align-items:center;margin-top:8px;color:#0f172a">
                    <div style="color:#0f172a"><span style="display:inline-block;width:22px;height:15px;background:{home_primary};border:1px solid #444;border-radius:3px"></span>
                    <b class="public-team-name" style="color:#0f172a">{home_name}</b><br><small class="kit-label" style="color:#475569">Hemmalagets tröjfärg</small></div>
                    <div class="match-score" style="font-size:20px;font-weight:700;color:#0f172a">{score}</div>
                    <div style="text-align:right;color:#0f172a"><b class="public-team-name" style="color:#0f172a">{away_name}</b> <span style="display:inline-block;width:22px;height:15px;background:{away_match_color};border:1px solid #444;border-radius:3px"></span>
                    <br><small class="kit-label" style="color:#475569">{'Bortalagets andra tröjfärg' if away_kit_used else 'Bortalagets tröjfärg'}</small></div>
                  </div>
                  {color_conflict_html}
                  <div class="match-weather" style="font-size:12px;color:#475569;text-align:center;margin-top:10px">{html.escape(weather_text)}</div>
                  <div class="match-referee" style="font-size:12px;color:#475569;text-align:center;margin-top:10px">Domare: {referees.get(match_row['referee_id'], 'Ej tillsatt')}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        if matches:
            st.caption("Väderprognos från Open-Meteo. Prognosen uppdateras automatiskt och kan förändras.")
    with tables:
        groups = all_rows("SELECT * FROM groups WHERE tournament_id=? ORDER BY name", (tournament_id,))
        for group in groups:
            st.subheader(group["name"])
            rows = [{"Pl": position, **data} for position, (_, data) in enumerate(calculate_table(group["id"], tournament), 1)]
            st.dataframe(centered_table(pd.DataFrame(rows)), hide_index=True, use_container_width=True)
    with statistics:
        rows = all_rows(
            """
            SELECT players.name AS player_name,teams.name AS team_name,
                   SUM(s.goals) AS goals,SUM(s.assists) AS assists,
                   SUM(s.yellow_cards) AS yellow_cards,SUM(s.red_cards) AS red_cards
            FROM player_match_stats s JOIN players ON players.id=s.player_id
            JOIN teams ON teams.id=players.team_id JOIN matches ON matches.id=s.match_id
            WHERE matches.tournament_id=? GROUP BY players.id,players.name,teams.name
            """,
            (tournament_id,),
        )
        st.subheader("Skytteliga")
        goal_rows = sorted(rows, key=lambda r: (-r["goals"], -r["assists"], r["player_name"].lower()))
        st.dataframe(pd.DataFrame([{"Pl": i, "Spelare": r["player_name"], "Lag": r["team_name"], "Mål": r["goals"]} for i, r in enumerate(goal_rows, 1) if r["goals"]]), hide_index=True, use_container_width=True)
        st.subheader("Assistliga")
        assist_rows = sorted(rows, key=lambda r: (-r["assists"], -r["goals"], r["player_name"].lower()))
        st.dataframe(pd.DataFrame([{"Pl": i, "Spelare": r["player_name"], "Lag": r["team_name"], "Assist": r["assists"]} for i, r in enumerate(assist_rows, 1) if r["assists"]]), hide_index=True, use_container_width=True)
    with playoffs:
        brackets = [] if tournament["playoff_format"] == "Inget slutspel" else brackets_for_display(tournament_id)[0]
        if not brackets:
            st.info("Turneringen har inget publicerat slutspel.")
        for bracket in brackets:
            st.subheader(bracket["name"])
            render_bracket_tree(bracket["id"], public=True)
    with information:
        st.subheader("Praktisk information")
        if visitor_rows:
            st.markdown(
                "<div class='public-information-card' style='padding:16px 18px;border:1px solid #cbd5e1;"
                "border-radius:12px;background:#f8fafc;color:#172033;display:grid;gap:12px;line-height:1.5'>"
                "<style>.public-information-card,.public-information-card div,.public-information-card b "
                "{color:#172033 !important}</style>" + "".join(visitor_rows) + "</div>",
                unsafe_allow_html=True,
            )
        else:
            st.info("Ingen praktisk information har publicerats ännu.")


init_db()


# SIDOMENY OCH TURNERING
st.sidebar.title("⚽ Turneringar")
with st.sidebar.expander("Skapa ny turnering"):
    with st.form("new_tournament", clear_on_submit=True):
        n = st.text_input("Namn")
        place = st.text_input("Spelort")
        start_date = st.date_input("Första cupdag")
        end_date = st.date_input("Sista cupdag", value=start_date)
        expected_teams = st.number_input("Planerat antal lag", 2, 500, 8)
        st.caption("Poängregler och övriga cupinställningar görs på Adminöversikt efter att turneringen har skapats.")
        if st.form_submit_button("Skapa", type="primary", use_container_width=True):
            if not n.strip():
                st.error("Ange ett namn.")
            elif end_date < start_date:
                st.error("Sista cupdagen får inte ligga före första cupdagen.")
            else:
                run(
                    """INSERT INTO tournaments(name,location,tournament_date,start_date,end_date,expected_team_count,points_win,points_draw,points_loss)
                    VALUES(?,?,?,?,?,?,?,?,?)""",
                    (n.strip(), place.strip(), start_date.isoformat(), start_date.isoformat(), end_date.isoformat(), expected_teams, 3, 1, 0),
                )
                st.rerun()

tournaments = all_rows("SELECT * FROM tournaments ORDER BY COALESCE(start_date,tournament_date) DESC,name")
if not tournaments:
    st.title("⚽ Fotbollsturnering")
    st.info("Skapa den första turneringen i vänstermenyn.")
    st.stop()

tid = st.sidebar.selectbox("Aktiv turnering", [t["id"] for t in tournaments], format_func=lambda x: next(t["name"] for t in tournaments if t["id"] == x))
tournament = next(t for t in tournaments if t["id"] == tid)
sync_placement_playoffs(tid, tournament["bronze_match"])
st.title(f"⚽ {tournament['name']}")
st.caption(f"{tournament['location'] or 'Spelort saknas'} · {cup_date_label(tournament)} · Planerat antal lag: {tournament['expected_team_count'] or 'Ej angivet'} · Poäng: {tournament['points_win']}/{tournament['points_draw']}/{tournament['points_loss']}")

view_mode = st.sidebar.radio("Visningsläge", ["Admin", "Turneringsvy"])
if view_mode == "Turneringsvy":
    if not tournament["is_published"]:
        st.info("Turneringen är ännu inte publicerad av administratören.")
        st.stop()
    render_public_view(tid, tournament)
    st.stop()

sidebar_rules = one_row("SELECT * FROM schedule_rules WHERE tournament_id=?", (tid,))
if sidebar_rules is None:
    run("INSERT INTO schedule_rules(tournament_id) VALUES(?)", (tid,))
    sidebar_rules = one_row("SELECT * FROM schedule_rules WHERE tournament_id=?", (tid,))
sidebar_scheduled = one_row(
    "SELECT COUNT(*) AS n FROM matches WHERE tournament_id=? AND scheduled_start IS NOT NULL",
    (tid,),
)["n"]
sidebar_errors, sidebar_warnings, _ = validate_schedule(tid, tournament, sidebar_rules)
st.sidebar.divider()
st.sidebar.subheader("Publicering")
if tournament["is_published"]:
    st.sidebar.success("Publicerad")
else:
    st.sidebar.caption("Turneringsvyn är ett utkast.")
sidebar_warnings_approved = st.sidebar.checkbox(
    "Jag har granskat schemavarningarna",
    disabled=not sidebar_warnings,
    key=f"sidebar_warning_approval_{tid}",
)
sidebar_publish_blocked = (
    not sidebar_scheduled or bool(sidebar_errors)
    or (bool(sidebar_warnings) and not sidebar_warnings_approved)
)
if st.sidebar.button("Publicera", type="primary", use_container_width=True, disabled=sidebar_publish_blocked):
    with db() as con:
        con.execute("UPDATE matches SET schedule_published=1 WHERE tournament_id=? AND scheduled_start IS NOT NULL", (tid,))
        con.execute("UPDATE tournaments SET is_published=1 WHERE id=?", (tid,))
        con.commit()
    st.rerun()
if st.sidebar.button("Avpublicera", use_container_width=True, disabled=not tournament["is_published"]):
    run("UPDATE tournaments SET is_published=0 WHERE id=?", (tid,))
    st.rerun()
if not sidebar_scheduled:
    st.sidebar.caption("Skapa spelschemat innan publicering.")
elif sidebar_errors:
    st.sidebar.caption(f"Åtgärda {len(sidebar_errors)} schemafel före publicering.")
elif sidebar_warnings and not sidebar_warnings_approved:
    st.sidebar.caption("Godkänn varningarna före publicering.")

st.header("Administration")
st.caption("Här ställs turneringens lag, grupper, regler, schema, domare och slutspel in. Lösenordsskydd läggs till senare.")

admin_overview_tab, setup_tab, squad_tab, referee_tab, schedule_tab, playoff_tab, match_tab, stats_tab, table_tab, leaders_tab = st.tabs([
    "Adminöversikt", "Lag och grupper", "Trupper", "Domare", "Skapa och publicera schema",
    "Slutspel", "Matcher och resultat", "Matchhändelser", "Tabeller", "Skytteligor"
])

with admin_overview_tab:
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
    with st.form("edit_tournament_basics"):
        st.markdown("#### Cup och deltagande")
        bn1, bn2 = st.columns(2)
        edited_name = bn1.text_input("Turneringens namn", value=tournament["name"])
        edited_location = bn2.text_input("Spelort", value=tournament["location"] or "")
        bc1, bc2, bc3 = st.columns(3)
        edited_start = bc1.date_input("Första cupdag", value=saved_start)
        edited_end = bc2.date_input("Sista cupdag", value=saved_end)
        edited_expected = bc3.number_input("Planerat antal lag", 2, 500, int(tournament["expected_team_count"] or 8))

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
            "Övrig information", value=tournament["public_information"] or "",
            placeholder="Exempel: Parkering finns vid skolan. Omklädningsrum öppnar 07.30. Hundar ska hållas kopplade.",
        )

        st.markdown("#### Poängregler och slutspel")
        bp1, bp2, bp3, bp4 = st.columns(4)
        edited_win = bp1.number_input("Poäng för vinst", 0, 10, int(tournament["points_win"]))
        edited_draw = bp2.number_input("Poäng för oavgjort", 0, 10, int(tournament["points_draw"]))
        edited_loss = bp3.number_input("Poäng för förlust", 0, 10, int(tournament["points_loss"]))
        edited_format = bp4.selectbox("Typ av slutspel", format_options, index=format_options.index(saved_format))
        edited_bronze = st.checkbox(
            "Skapa bronsmatch automatiskt när slutspelsträdet har minst fyra lag",
            value=bool(tournament["bronze_match"]),
            disabled=edited_format == "Inget slutspel",
        )

        st.markdown("#### Match- och schemaregler")
        br1, br2, br3 = st.columns(3)
        edited_first_time = br1.time_input("Första avspark", value=datetime.strptime(overview_rules["first_match_time"], "%H:%M").time())
        edited_halves = br2.number_input("Antal halvlekar", 1, 4, int(overview_rules["halves"]))
        edited_minutes_half = br3.number_input("Minuter per halvlek", 1, 120, int(overview_rules["minutes_per_half"]))
        br4, br5 = st.columns(2)
        edited_halftime = br4.number_input("Halvtidspaus (minuter)", 0, 60, int(overview_rules["halftime_minutes"]))
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
        edited_latest = br8.time_input("Senaste tillåtna avspark", value=datetime.strptime(overview_rules["latest_kickoff_time"], "%H:%M").time())
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
                ])
                with db() as con:
                    con.execute(
                        """UPDATE tournaments SET name=?,location=?,tournament_date=?,start_date=?,end_date=?,expected_team_count=?,
                        points_win=?,points_draw=?,points_loss=?,playoff_format=?,bronze_match=?,arena_address=?,kiosk_available=?,
                        kiosk_information=?,public_information=? WHERE id=?""",
                        (edited_name.strip(), edited_location.strip(), edited_start.isoformat(), edited_start.isoformat(), edited_end.isoformat(),
                         edited_expected, edited_win, edited_draw, edited_loss, edited_format, int(edited_bronze), edited_address.strip(),
                         int(bool(edited_kiosk_info.strip())), edited_kiosk_info.strip(), edited_public_info.strip(), tid),
                    )
                    con.execute(
                        """UPDATE schedule_rules SET first_match_time=?,halves=?,minutes_per_half=?,halftime_minutes=?,pitch_break_minutes=?,
                        avoid_consecutive_matches=?,consecutive_match_break_minutes=?,pitch_count=?,latest_kickoff_time=?,referee_mode=? WHERE tournament_id=?""",
                        (edited_first_time.strftime("%H:%M"), edited_halves, edited_minutes_half, edited_halftime, edited_pitch_break,
                         int(edited_avoid_consecutive), edited_consecutive_break, edited_pitch_count,
                         edited_latest.strftime("%H:%M"), edited_referee_mode, tid),
                    )
                    if scheduling_changed:
                        con.execute("UPDATE matches SET scheduled_start=NULL,pitch_number=NULL,schedule_published=0,schedule_locked=0 WHERE tournament_id=?", (tid,))
                        con.execute("UPDATE tournaments SET is_published=0 WHERE id=?", (tid,))
                    con.commit()
                st.session_state["overview_saved_message"] = "Grunduppgifterna sparades. Spelschemat behöver genereras och publiceras på nytt." if scheduling_changed else "Grunduppgifterna sparades."
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
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Grupper", len(admin_groups))
    c2.metric("Lag", len(admin_teams))
    c3.metric("Matcher", len(admin_matches))
    c4.metric("Tävlingsformat", tournament["playoff_format"])
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
    with st.expander("⚠️ Riskzon – radera hela turneringen"):
        st.error(
            "Radering tar permanent bort turneringen inklusive grupper, lag, spelare, domare, matcher, "
            "resultat, matchhändelser, tabeller och slutspel. Åtgärden kan inte ångras i appen."
        )
        delete_selected = st.checkbox(
            f"Markera {tournament['name']} för borttagning",
            key=f"delete_tournament_selected_{tid}",
        )

        @st.dialog("Är du säker?")
        def confirm_tournament_deletion():
            st.warning(
                f"Turneringen **{tournament['name']}** och all tillhörande information kommer att raderas permanent."
            )
            confirm_delete, cancel_delete = st.columns(2)
            if confirm_delete.button("Ja, radera permanent", type="primary", use_container_width=True):
                with db() as con:
                    con.execute("DELETE FROM tournaments WHERE id=?", (tid,))
                    con.commit()
                st.rerun()
            if cancel_delete.button("Avbryt", use_container_width=True):
                st.rerun()

        if st.button(
            "Radera markerad turnering",
            disabled=not delete_selected,
            key=f"open_delete_tournament_dialog_{tid}",
        ):
            confirm_tournament_deletion()


with setup_tab:
    left, right = st.columns(2)
    with left:
        st.subheader("Grupper")
        with st.form("new_group", clear_on_submit=True):
            group_name = st.text_input("Gruppnamn", placeholder="Grupp A")
            if st.form_submit_button("Lägg till grupp", type="primary"):
                if group_name.strip():
                    run("INSERT INTO groups(tournament_id,name) VALUES(?,?)", (tid, group_name.strip()))
                    st.rerun()
                st.error("Ange ett gruppnamn.")
        groups = all_rows("SELECT * FROM groups WHERE tournament_id=? ORDER BY name", (tid,))
        for g in groups:
            st.write(f"• {g['name']}")
    with right:
        st.subheader("Lägg till lag")
        groups = all_rows("SELECT * FROM groups WHERE tournament_id=? ORDER BY name", (tid,))
        with st.form("new_team", clear_on_submit=True):
            team_name = st.text_input("Lagnamn")
            group_choice = st.selectbox("Grupp", [None] + [g["id"] for g in groups], format_func=lambda x: "Ingen grupp ännu" if x is None else next(g["name"] for g in groups if g["id"] == x))
            col1, col2 = st.columns(2)
            primary = col1.color_picker("Huvudfärg", "#111827")
            secondary = col2.color_picker("Andrafärg", "#FFFFFF")
            distance = st.number_input("Resväg i kilometer", 0, 5000, 0)
            travel_note = st.text_input("Resekommentar", placeholder="Exempel: Reser samma morgon")
            if st.form_submit_button("Lägg till lag", type="primary"):
                if team_name.strip():
                    run(
                        """INSERT INTO teams(tournament_id,name,group_id,primary_color,secondary_color,distance_km,travel_note)
                        VALUES(?,?,?,?,?,?,?)""",
                        (tid, team_name.strip(), group_choice, primary, secondary, distance, travel_note.strip()),
                    )
                    st.rerun()
                st.error("Ange ett lagnamn.")
    st.divider()
    st.subheader("Placera lagen i rätt grupp")
    groups = all_rows("SELECT * FROM groups WHERE tournament_id=? ORDER BY name", (tid,))
    teams = all_rows("SELECT * FROM teams WHERE tournament_id=? ORDER BY name", (tid,))
    if not teams:
        st.info("Inga lag är registrerade.")
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
    edit_team_col, edit_group_col = st.columns(2)
    with edit_team_col:
        with st.expander("Redigera eller ta bort lag"):
            if teams:
                edit_team_id = st.selectbox("Välj lag", [t["id"] for t in teams], format_func=lambda x: next(t["name"] for t in teams if t["id"] == x), key="edit_team")
                edit_team = next(t for t in teams if t["id"] == edit_team_id)
                with st.form("edit_team_form"):
                    edited_name = st.text_input("Lagnamn", value=edit_team["name"])
                    ec1, ec2 = st.columns(2)
                    edited_primary = ec1.color_picker("Huvudfärg", edit_team["primary_color"])
                    edited_secondary = ec2.color_picker("Andrafärg", edit_team["secondary_color"])
                    edited_distance = st.number_input("Resväg i kilometer", 0, 5000, int(edit_team["distance_km"] or 0))
                    edited_travel_note = st.text_input("Resekommentar", value=edit_team["travel_note"] or "")
                    if st.form_submit_button("Spara ändringar", type="primary"):
                        if edited_name.strip():
                            run(
                                """UPDATE teams SET name=?,primary_color=?,secondary_color=?,distance_km=?,travel_note=? WHERE id=?""",
                                (edited_name.strip(), edited_primary, edited_secondary, edited_distance, edited_travel_note.strip(), edit_team_id),
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
                    saved_rules = one_row("SELECT * FROM schedule_rules WHERE tournament_id=?", (tid,))
                    if saved_rules:
                        generate_schedule(tid, tournament, saved_rules, preserve_existing=True)
                    st.rerun()
            else:
                st.info("Det finns inga lag att redigera.")
    with edit_group_col:
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


with squad_tab:
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
        st.dataframe(pd.DataFrame([{"Nr": p["player_number"], "Spelare": p["name"], "Födelseår": p["birth_year"], "Position": p["position"]} for p in players]), hide_index=True, use_container_width=True)


with referee_tab:
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
    st.dataframe(pd.DataFrame([{"Namn": r["name"], "Telefon": r["phone"], "E-post": r["email"]} for r in refs]), hide_index=True, use_container_width=True)


with schedule_tab:
    st.subheader("Skapa spelschema")
    st.caption("En knapp skapar alla gruppmöten och schemalägger dem samtidigt för samtliga grupper.")
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
        f"matchtid totalt {match_minutes} min · första avspark {rules['first_match_time']} · senaste avspark {rules['latest_kickoff_time']} · "
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
    schedule_errors, schedule_warnings, schedule_quality = validate_schedule(tid, tournament, rules)

    st.markdown("#### 2. Skapa och generera spelschema")
    with st.container(border=True):
        status1, status2, status3 = st.columns(3)
        status1.metric("Gruppspelsmatcher", group_match_total)
        status2.metric("Schemalagda matcher", scheduled_total)
        status3.metric("Ej publicerade", unpublished_total)
        create_disabled = not schedule_groups or unassigned_count > 0 or bool(too_small_groups)
        if st.button("Skapa matcher och generera spelschema", type="primary", use_container_width=True, disabled=create_disabled):
            created, ready_groups, skipped_groups = create_all_group_matches(tid)
            count, unresolved, warning = generate_schedule(tid, tournament, rules)
            parts = [
                f"Alla {ready_groups} grupper kontrollerades och {created} saknade matcher skapades.",
                f"{count} matcher schemalades.",
            ]
            if unresolved:
                parts.append(f"{unresolved} matcher kunde inte schemaläggas.")
            if warning:
                parts.append(warning)
            st.session_state["schedule_message"] = ("warning" if unresolved or warning else "success", " ".join(parts))
            st.rerun()
        if create_disabled:
            problems = []
            if not schedule_groups:
                problems.append("skapa minst en grupp")
            if unassigned_count:
                problems.append(f"placera {unassigned_count} lag i en grupp")
            if too_small_groups:
                problems.append("lägg minst två lag i: " + ", ".join(too_small_groups))
            st.warning("Innan gruppmöten kan skapas måste du " + "; ".join(problems) + ".")
        elif scheduled_total == 0:
            st.info("Klicka på knappen ovan för att både skapa gruppmöten och generera hela spelschemat.")
        elif schedule_errors:
            st.error(f"Schemat har {len(schedule_errors)} fel och kan inte publiceras. Se schemakontrollen nedan.")
        elif schedule_warnings:
            st.warning("Schemat har varningar. Granska dem och godkänn dem i vänsterspalten före publicering.")
        elif unpublished_total:
            st.warning("Schemat är ett utkast. Kontrollera matchlistan och publicera sedan från vänsterspalten.")
        else:
            st.success("Det aktuella spelschemat är publicerat i Turneringsvyn.")

        st.markdown("**Kontroll per grupp**")
        group_status_rows = []
        for group in schedule_groups:
            team_count = one_row("SELECT COUNT(*) AS n FROM teams WHERE group_id=?", (group["id"],))["n"]
            expected_matches = team_count * (team_count - 1) // 2
            created_matches = one_row("SELECT COUNT(*) AS n FROM matches WHERE group_id=? AND stage='Gruppspel'", (group["id"],))["n"]
            scheduled_matches_count = one_row("SELECT COUNT(*) AS n FROM matches WHERE group_id=? AND stage='Gruppspel' AND scheduled_start IS NOT NULL", (group["id"],))["n"]
            published_matches = one_row("SELECT COUNT(*) AS n FROM matches WHERE group_id=? AND stage='Gruppspel' AND schedule_published=1", (group["id"],))["n"]
            group_status_rows.append({
                "Grupp": group["name"], "Lag": team_count, "Förväntade möten": expected_matches,
                "Skapade": created_matches, "Schemalagda": scheduled_matches_count, "Publicerade": published_matches,
            })
        if group_status_rows:
            st.dataframe(pd.DataFrame(group_status_rows), hide_index=True, use_container_width=True)

    st.markdown("#### 3. Schemakontroll")
    vc1, vc2, vc3 = st.columns(3)
    vc1.metric("Fel", len(schedule_errors))
    vc2.metric("Varningar", len(schedule_warnings))
    vc3.metric("Kontrollerade lag", len(schedule_quality))
    if schedule_errors:
        st.error("\n".join(f"• {message}" for message in schedule_errors))
    elif scheduled_total:
        st.success("Inga blockerande schemakrockar hittades.")
    if schedule_warnings:
        with st.expander(f"Visa {len(schedule_warnings)} varningar"):
            for message in schedule_warnings:
                st.warning(message)
    if schedule_quality:
        st.dataframe(centered_table(pd.DataFrame(schedule_quality)), hide_index=True, use_container_width=True)

    travel_teams = all_rows("SELECT * FROM teams WHERE tournament_id=? ORDER BY name", (tid,))
    st.subheader("Reseinformation för lagen")
    st.dataframe(
        pd.DataFrame([
            {
                "Lag": t["name"],
                "Resväg km": t["distance_km"],
                "Kommentar": t["travel_note"] or "",
            }
            for t in travel_teams
        ]),
        hide_index=True,
        use_container_width=True,
    )
    adjustable_matches = all_rows(
        "SELECT * FROM matches WHERE tournament_id=? AND scheduled_start IS NOT NULL ORDER BY scheduled_start,pitch_number,id",
        (tid,),
    )
    if adjustable_matches:
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
                kit_note = f"⚠ {away['name']} behöver ett ytterligare avvikande ställ" if away else "⚠ Färgkrock"
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
                "Hemmafärg": color_swatch(home_kit_color) if home else None,
                "Bortalag": away["name"] if away else source_label(m["away_source"]),
                "Bortafärg": color_swatch(away_kit_color) if away else None,
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
            generate_schedule(tid, tournament, rules, preserve_existing=True)
            st.success("Resultaten sparades.")
        st.caption("Målskyttar, assist, varningar och utvisningar registreras under fliken Matchhändelser och visas därefter automatiskt här.")


with match_tab:
    refs = all_rows("SELECT * FROM referees WHERE tournament_id=? ORDER BY name", (tid,))
    st.subheader("Registrera resultat och domare")
    st.caption("Matcherna skapas automatiskt från gruppindelningen och den valda slutspelsmodellen.")
    if "bulk_result_message" in st.session_state:
        st.success(st.session_state.pop("bulk_result_message"))
    matches = all_rows("SELECT * FROM matches WHERE tournament_id=? ORDER BY CASE stage WHEN 'Gruppspel' THEN 0 ELSE 1 END, group_id, bracket_id, round_no, match_no", (tid,))
    if not matches:
        st.info("Inga matcher är skapade.")
    else:
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
                    "Domare": referee_names.get(m["referee_id"], "Ej tillsatt"),
                })
            edited_results = st.data_editor(
                pd.DataFrame(result_rows),
                hide_index=True,
                use_container_width=True,
                disabled=["match_id", "Match", "Fas", "Hemmalag", "Bortalag"],
                column_order=["Match", "Fas", "Hemmalag", "Hemmamål", "Bortamål", "Bortalag", "Hemmastraffar", "Bortastraffar", "Domare"],
                column_config={
                    "Hemmamål": st.column_config.NumberColumn(min_value=0, max_value=99, step=1),
                    "Bortamål": st.column_config.NumberColumn(min_value=0, max_value=99, step=1),
                    "Hemmastraffar": st.column_config.NumberColumn("Straffar hemma", min_value=0, max_value=99, step=1),
                    "Bortastraffar": st.column_config.NumberColumn("Straffar borta", min_value=0, max_value=99, step=1),
                    "Domare": st.column_config.SelectboxColumn(options=referee_options),
                },
                key=f"bulk_results_{tid}",
            )
            st.caption("Lämna båda målkolumnerna tomma för en ospelad match. Straffar används bara vid oavgjorda slutspelsmatcher.")
            if st.button("Spara alla resultat", type="primary", use_container_width=True):
                updates = []
                errors = []
                for _, row in edited_results.iterrows():
                    home_score = None if pd.isna(row["Hemmamål"]) else int(row["Hemmamål"])
                    away_score = None if pd.isna(row["Bortamål"]) else int(row["Bortamål"])
                    home_penalties = None if pd.isna(row["Hemmastraffar"]) else int(row["Hemmastraffar"])
                    away_penalties = None if pd.isna(row["Bortastraffar"]) else int(row["Bortastraffar"])
                    if (home_score is None) != (away_score is None):
                        errors.append(f"{row['Hemmalag']}–{row['Bortalag']}: fyll i båda målresultaten eller lämna båda tomma.")
                        continue
                    if row["Fas"] != "Gruppspel" and home_score is not None and home_score == away_score:
                        if home_penalties is None or away_penalties is None or home_penalties == away_penalties:
                            errors.append(f"{row['Hemmalag']}–{row['Bortalag']}: en oavgjord slutspelsmatch måste få en vinnare efter straffar.")
                            continue
                    else:
                        home_penalties = away_penalties = None
                    referee_id = referee_ids_by_name.get(row["Domare"])
                    updates.append((home_score, away_score, home_penalties, away_penalties, referee_id, int(row["match_id"])))
                if errors:
                    st.error("\n".join(f"• {message}" for message in errors))
                else:
                    with db() as con:
                        con.executemany(
                            "UPDATE matches SET home_score=?,away_score=?,home_penalties=?,away_penalties=?,referee_id=? WHERE id=?",
                            updates,
                        )
                        con.commit()
                    saved_rules = one_row("SELECT * FROM schedule_rules WHERE tournament_id=?", (tid,))
                    if saved_rules:
                        generate_schedule(tid, tournament, saved_rules, preserve_existing=True)
                    st.session_state["bulk_result_message"] = f"{len(updates)} matchresultat sparades."
                    st.rerun()


with stats_tab:
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
            if st.button(f"Spara mål och assist för {selected_team['name']}", type="primary", key=f"save_stats_{stat_match_id}_{selected_team_id}"):
                with db() as con:
                    for _, row in edited.iterrows():
                        goals = int(row["Mål"] or 0)
                        assists = int(row["Assist"] or 0)
                        yellow_cards = int(row["Varningar"] or 0)
                        red_cards = int(row["Utvisningar"] or 0)
                        con.execute(
                            """
                            INSERT INTO player_match_stats(match_id,player_id,goals,assists,yellow_cards,red_cards)
                            VALUES(?,?,?,?,?,?)
                            ON CONFLICT(match_id,player_id)
                            DO UPDATE SET goals=excluded.goals, assists=excluded.assists,
                                yellow_cards=excluded.yellow_cards, red_cards=excluded.red_cards
                            """,
                            (stat_match_id, int(row["player_id"]), goals, assists, yellow_cards, red_cards),
                        )
                    con.commit()
                st.success("Statistiken sparades.")
            registered_goals = int(edited["Mål"].sum())
            expected_goals = stat_match["home_score"] if selected_team_id == home_team_id else stat_match["away_score"]
            if registered_goals != expected_goals:
                st.warning(f"Registrerade spelarmål: {registered_goals}. Matchresultatet visar {expected_goals} mål. Skillnaden kan exempelvis vara självmål.")


with table_tab:
    groups = all_rows("SELECT * FROM groups WHERE tournament_id=? ORDER BY name", (tid,))
    if not groups:
        st.info("Skapa minst en grupp.")
    for g in groups:
        st.subheader(g["name"])
        table = calculate_table(g["id"], tournament)
        rows = []
        for pos, (_, data) in enumerate(table, 1):
            rows.append({"Pl": pos, **data})
        st.dataframe(centered_table(pd.DataFrame(rows)), hide_index=True, use_container_width=True)
        st.caption("Sortering: poäng, målskillnad, gjorda mål, lagnamn.")


with leaders_tab:
    st.subheader("Skytteliga")
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
    goal_rows = sorted(leaders, key=lambda r: (-r["goals"], -r["assists"], r["player_name"].lower()))
    if goal_rows:
        st.dataframe(pd.DataFrame([{"Pl": i, "Spelare": r["player_name"], "Lag": r["team_name"], "Mål": r["goals"]} for i, r in enumerate(goal_rows, 1)]), hide_index=True, use_container_width=True)
    else:
        st.info("Inga målskyttar har registrerats.")
    st.subheader("Assistliga")
    assist_rows = sorted(leaders, key=lambda r: (-r["assists"], -r["goals"], r["player_name"].lower()))
    if assist_rows:
        st.dataframe(pd.DataFrame([{"Pl": i, "Spelare": r["player_name"], "Lag": r["team_name"], "Assist": r["assists"]} for i, r in enumerate(assist_rows, 1)]), hide_index=True, use_container_width=True)
    else:
        st.info("Inga assist har registrerats.")
    st.subheader("Varningar och utvisningar")
    card_rows = sorted(leaders, key=lambda r: (-r["red_cards"], -r["yellow_cards"], r["player_name"].lower()))
    card_rows = [r for r in card_rows if r["yellow_cards"] or r["red_cards"]]
    if card_rows:
        st.dataframe(pd.DataFrame([{"Spelare": r["player_name"], "Lag": r["team_name"], "Varningar": r["yellow_cards"], "Utvisningar": r["red_cards"]} for r in card_rows]), hide_index=True, use_container_width=True)
    else:
        st.info("Inga varningar eller utvisningar har registrerats.")


with playoff_tab:
    groups = all_rows("SELECT * FROM groups WHERE tournament_id=? ORDER BY name", (tid,))
    teams = all_rows("SELECT * FROM teams WHERE tournament_id=? ORDER BY name", (tid,))
    placement_format = PLACEMENT_PLAYOFF_FORMAT
    format_options = ["Inget slutspel", "A- och B-slutspel", placement_format]
    stored_format = placement_format if tournament["playoff_format"] == "Flera egna slutspel" else tournament["playoff_format"]
    current_format = stored_format if stored_format in format_options else "Inget slutspel"
    selected_format = current_format
    st.subheader("Slutspelsmodell")
    st.info(f"Vald modell: **{selected_format}**. Modellen ändras endast under Adminöversikt → Cupens grunduppgifter.")
    if selected_format == "A- och B-slutspel":
        st.info("Skapa två träd nedan: ett med namnet A-slutspel och ett med namnet B-slutspel. Välj sedan vilka gruppplaceringar som ska fylla platserna i respektive träd.")
    elif selected_format == placement_format:
        st.info("Ettorna i grupperna möter andra gruppettor, tvåorna möter andra grupptvåor och så vidare. Appen skapar placeringsslutspelen automatiskt.")
    st.divider()
    existing_brackets = all_rows("SELECT * FROM brackets WHERE tournament_id=?", (tid,))
    team_counts = {
        group["id"]: one_row("SELECT COUNT(*) AS n FROM teams WHERE group_id=?", (group["id"],))["n"]
        for group in groups
    }
    automatic_specs = []
    automatic_error = ""
    if selected_format == "A- och B-slutspel":
        if len(groups) != 2 or any(team_counts[group["id"]] < 4 for group in groups):
            automatic_error = "A- och B-slutspel kräver exakt två grupper med minst fyra lag i varje. Ändra gruppindelningen på adminsidan."
        else:
            group_a, group_b = groups
            automatic_specs = [
                ("A-slutspel", 4, [f"group:{group_a['id']}:1", f"group:{group_b['id']}:2", f"group:{group_b['id']}:1", f"group:{group_a['id']}:2"]),
                ("B-slutspel", 4, [f"group:{group_a['id']}:3", f"group:{group_b['id']}:4", f"group:{group_b['id']}:3", f"group:{group_a['id']}:4"]),
            ]
            st.success(f"A: 1:a {group_a['name']}–2:a {group_b['name']} och 1:a {group_b['name']}–2:a {group_a['name']}. B: motsvarande möten mellan treor och fyror.")
    elif selected_format == placement_format:
        automatic_specs, automatic_error = placement_playoff_specs(tid)
        if not automatic_error:
            st.success("Ett separat slutspel skapas automatiskt för varje gruppplacering som finns i samtliga grupper.")

    if selected_format == "Inget slutspel":
        st.info("Ingen cupbyggare behövs eftersom modellen är Inget slutspel. Befintliga träd kan tas bort nedan.")
    elif automatic_error:
        st.error(automatic_error)
    elif selected_format == placement_format:
        st.info("Placeringsmatcherna skapas och uppdateras automatiskt. Ingen separat genereringsknapp behövs för den här modellen.")
    else:
        with st.form("automatic_playoff_builder"):
            if tournament["bronze_match"]:
                st.caption("Bronsmatch skapas automatiskt i träd med minst fyra lag enligt valet på Adminöversikten.")
            replace_existing = st.checkbox(
                "Jag förstår att befintliga slutspel och registrerade slutspelsresultat ersätts",
                disabled=not existing_brackets,
            )
            generate_automatic = st.form_submit_button(
                "Generera hela slutspelet automatiskt",
                type="primary",
                disabled=bool(existing_brackets) and not replace_existing,
            )
            if generate_automatic:
                with db() as con:
                    con.execute("DELETE FROM brackets WHERE tournament_id=?", (tid,))
                    con.commit()
                for bracket_name, bracket_size, bracket_sources in automatic_specs:
                    create_bracket(tid, bracket_name, bracket_size, bool(tournament["bronze_match"]) and bracket_size >= 4, bracket_sources)
                saved_rules = one_row("SELECT * FROM schedule_rules WHERE tournament_id=?", (tid,))
                if saved_rules:
                    generate_schedule(tid, tournament, saved_rules, preserve_existing=True)
                st.rerun()
    st.divider()
    brackets, duplicate_brackets = brackets_for_display(tid)
    if duplicate_brackets:
        duplicate_names = ", ".join(bracket["name"] for bracket in duplicate_brackets)
        st.warning(f"Äldre dubbla slutspel hittades ({duplicate_names}). De döljs från Turneringsvyn så att endast ett A- och ett B-slutspel visas.")
        with st.expander("Granska och rensa äldre dubbletter"):
            for duplicate in duplicate_brackets:
                completed = one_row(
                    "SELECT COUNT(*) AS n FROM matches WHERE bracket_id=? AND home_score IS NOT NULL",
                    (duplicate["id"],),
                )["n"]
                st.write(f"{duplicate['name']} · databas-id {duplicate['id']} · spelade matcher: {completed}")
                confirmed = st.checkbox(
                    f"Bekräfta borttagning av dubblett {duplicate['name']} (id {duplicate['id']})",
                    key=f"confirm_duplicate_{duplicate['id']}",
                )
                if st.button(
                    f"Ta bort dubblett id {duplicate['id']}",
                    disabled=not confirmed,
                    key=f"delete_duplicate_{duplicate['id']}",
                ):
                    run("DELETE FROM brackets WHERE id=?", (duplicate["id"],))
                    st.rerun()
    if not brackets:
        st.info("Inget slutspel är skapat. Gruppspelet fungerar ändå som vanligt.")
    for bracket in brackets:
        st.subheader(bracket["name"])
        confirm_bracket_delete = st.checkbox(f"Bekräfta borttagning av {bracket['name']}", key=f"confirm_bracket_{bracket['id']}")
        if st.button(f"Ta bort {bracket['name']}", disabled=not confirm_bracket_delete, key=f"delete_bracket_{bracket['id']}"):
            run("DELETE FROM brackets WHERE id=?", (bracket["id"],))
            st.rerun()
        render_bracket_tree(bracket["id"], public=False)
