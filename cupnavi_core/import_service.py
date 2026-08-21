import re
from dataclasses import dataclass


TEAM_FIELDS = {
    "Lag": {"required": True, "aliases": ["lag", "team", "team name", "lagnamn", "club", "klubb"]},
    "Grupp": {"required": False, "aliases": ["grupp", "group", "pool"]},
    "Hemmafärg": {"required": False, "aliases": ["hemmafärg", "hemmafarg", "home color", "home colour", "primary color"]},
    "Bortafärg": {"required": False, "aliases": ["bortafärg", "bortafarg", "away color", "away colour", "secondary color"]},
    "Resväg km": {"required": False, "aliases": ["resväg km", "resvag km", "distance km", "distance", "resväg"]},
    "Senare första match": {"required": False, "aliases": ["senare första match", "senare forsta match", "late first match", "late start"]},
    "Första match tidigast": {"required": False, "aliases": ["första match tidigast", "forsta match tidigast", "earliest first time", "earliest start"]},
    "Kommentar": {"required": False, "aliases": ["kommentar", "comment", "note", "anteckning"]},
}

PLAYER_FIELDS = {
    "Lag": {"required": True, "aliases": ["lag", "team", "team name", "lagnamn"]},
    "Spelare": {"required": True, "aliases": ["spelare", "player", "player name", "namn", "name"]},
    "Tröjnummer": {"required": False, "aliases": ["tröjnummer", "trojnummer", "nummer", "shirt number", "jersey number", "number"]},
    "Födelseår": {"required": False, "aliases": ["födelseår", "fodelsear", "birth year", "birthyear", "year of birth"]},
    "Position": {"required": False, "aliases": ["position", "pos"]},
}


def _norm(value):
    value = str(value or "").strip().casefold()
    value = (
        value.replace("å", "a")
        .replace("ä", "a")
        .replace("ö", "o")
        .replace("_", " ")
        .replace("-", " ")
    )
    return " ".join(value.split())


def auto_map_columns(columns, fields):
    normalized = {_norm(column): column for column in columns}
    result = {}
    for target, spec in fields.items():
        candidates = [_norm(target)] + [_norm(alias) for alias in spec["aliases"]]
        result[target] = next((normalized[c] for c in candidates if c in normalized), None)
    return result


def clean_text(value):
    if value is None:
        return ""
    # pandas NaN compares unequal to itself
    try:
        if value != value:
            return ""
    except Exception:
        pass
    return str(value).strip()


def parse_optional_int(value, minimum=None, maximum=None):
    text = clean_text(value)
    if not text:
        return None
    try:
        number = int(float(text.replace(",", ".")))
    except (TypeError, ValueError):
        raise ValueError(f"'{text}' är inte ett heltal")
    if minimum is not None and number < minimum:
        raise ValueError(f"{number} är mindre än {minimum}")
    if maximum is not None and number > maximum:
        raise ValueError(f"{number} är större än {maximum}")
    return number


def parse_bool(value):
    return _norm(clean_text(value)) in {
        "ja", "yes", "true", "1", "x", "j", "y", "sen", "later"
    }


def normalize_color(value, default):
    text = clean_text(value)
    if not text:
        return default
    if re.fullmatch(r"#[0-9a-fA-F]{6}", text):
        return text.upper()
    raise ValueError(f"'{text}' är inte en giltig HEX-färg, exempel #1D4ED8")


def normalize_time(value):
    text = clean_text(value)
    if not text:
        return None
    # Excel may give HH:MM:SS or a datetime-ish string.
    match = re.search(r"(?<!\d)([01]?\d|2[0-3]):([0-5]\d)(?::[0-5]\d)?", text)
    if not match:
        raise ValueError(f"'{text}' är inte en giltig tid, använd HH:MM")
    return f"{int(match.group(1)):02d}:{match.group(2)}"


def build_team_import_plan(dataframe, mapping, existing_names, max_new_teams=None):
    records = []
    issues = []
    seen = {str(name).strip().casefold() for name in existing_names}

    for row_index, (_, row) in enumerate(dataframe.iterrows(), start=2):
        name = clean_text(row.get(mapping.get("Lag"))) if mapping.get("Lag") else ""
        if not name:
            issues.append({"Rad": row_index, "Nivå": "Fel", "Meddelande": "Lagnamn saknas."})
            continue

        folded = name.casefold()
        if folded in seen:
            issues.append({"Rad": row_index, "Nivå": "Hoppa över", "Meddelande": f"'{name}' finns redan eller förekommer flera gånger i filen."})
            continue

        try:
            distance = parse_optional_int(
                row.get(mapping.get("Resväg km")) if mapping.get("Resväg km") else None,
                minimum=0,
                maximum=5000,
            ) or 0
            home_color = normalize_color(
                row.get(mapping.get("Hemmafärg")) if mapping.get("Hemmafärg") else None,
                "#111827",
            )
            away_color = normalize_color(
                row.get(mapping.get("Bortafärg")) if mapping.get("Bortafärg") else None,
                "#FFFFFF",
            )
            earliest = normalize_time(
                row.get(mapping.get("Första match tidigast")) if mapping.get("Första match tidigast") else None
            )
        except ValueError as exc:
            issues.append({"Rad": row_index, "Nivå": "Fel", "Meddelande": f"{name}: {exc}"})
            continue

        record = {
            "name": name,
            "group": clean_text(row.get(mapping.get("Grupp"))) if mapping.get("Grupp") else "",
            "home_color": home_color,
            "away_color": away_color,
            "distance_km": distance,
            "late_first_match": parse_bool(
                row.get(mapping.get("Senare första match")) if mapping.get("Senare första match") else None
            ),
            "earliest_first_time": earliest,
            "comment": clean_text(row.get(mapping.get("Kommentar"))) if mapping.get("Kommentar") else "",
            "source_row": row_index,
        }
        records.append(record)
        seen.add(folded)

    if max_new_teams is not None and len(records) > max_new_teams:
        issues.append({
            "Rad": "–",
            "Nivå": "Fel",
            "Meddelande": (
                f"Filen innehåller {len(records)} nya lag men det finns bara plats för "
                f"{max_new_teams} enligt turneringens planerade maxantal."
            ),
        })

    return records, issues


def build_player_import_plan(dataframe, mapping, team_lookup, existing_players):
    records = []
    issues = []
    seen = {(int(team_id), str(name).strip().casefold()) for team_id, name in existing_players}

    for row_index, (_, row) in enumerate(dataframe.iterrows(), start=2):
        team_name = clean_text(row.get(mapping.get("Lag"))) if mapping.get("Lag") else ""
        player_name = clean_text(row.get(mapping.get("Spelare"))) if mapping.get("Spelare") else ""

        if not team_name or not player_name:
            issues.append({"Rad": row_index, "Nivå": "Fel", "Meddelande": "Både Lag och Spelare måste vara ifyllda."})
            continue

        team_id = team_lookup.get(team_name.casefold())
        if team_id is None:
            issues.append({"Rad": row_index, "Nivå": "Fel", "Meddelande": f"Laget '{team_name}' finns inte i turneringen."})
            continue

        key = (int(team_id), player_name.casefold())
        if key in seen:
            issues.append({"Rad": row_index, "Nivå": "Hoppa över", "Meddelande": f"{player_name} finns redan i {team_name} eller förekommer flera gånger i filen."})
            continue

        try:
            number = parse_optional_int(
                row.get(mapping.get("Tröjnummer")) if mapping.get("Tröjnummer") else None,
                minimum=0,
                maximum=999,
            )
            birth_year = parse_optional_int(
                row.get(mapping.get("Födelseår")) if mapping.get("Födelseår") else None,
                minimum=1900,
                maximum=2100,
            )
        except ValueError as exc:
            issues.append({"Rad": row_index, "Nivå": "Fel", "Meddelande": f"{player_name}: {exc}"})
            continue

        records.append({
            "team_id": int(team_id),
            "team_name": team_name,
            "player_name": player_name,
            "player_number": number,
            "birth_year": birth_year,
            "position": clean_text(row.get(mapping.get("Position"))) if mapping.get("Position") else "",
            "source_row": row_index,
        })
        seen.add(key)

    return records, issues
