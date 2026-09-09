import json
import re
from urllib.request import Request, urlopen

ALLOWED_PATTERNS = ["Helfärgad", "Vertikala ränder", "Horisontella ränder", "Rutigt", "Delad"]
ALLOWED_CONFIDENCE = ["low", "medium", "high"]
MAX_SOURCES = 5
MAX_SEARCH_ATTEMPTS = 3


def _extract_output_text(payload):
    for item in payload.get("output", []) or []:
        if item.get("type") != "message":
            continue
        for content in item.get("content", []) or []:
            if content.get("type") == "output_text" and content.get("text"):
                return str(content["text"])
    if payload.get("output_text"):
        return str(payload["output_text"])
    raise ValueError("AI-tjänsten returnerade inget läsbart svar.")


def _normalize_hex(value, fallback):
    text = str(value or "").strip().upper()
    if re.fullmatch(r"#[0-9A-F]{6}", text):
        return text
    return fallback


def normalize_kit_suggestion(payload):
    payload = payload or {}
    confidence = str(payload.get("confidence") or "low").lower()
    if confidence not in ALLOWED_CONFIDENCE:
        confidence = "low"
    sources = [str(url).strip() for url in (payload.get("sources") or []) if str(url).strip().startswith(("http://", "https://"))][:MAX_SOURCES]
    home_verified = bool(payload.get("home_verified", payload.get("found")))
    away_verified = bool(payload.get("away_verified", payload.get("found")))
    found = bool(payload.get("found")) and bool(sources) and (home_verified or away_verified)

    def pattern(name):
        value = str(payload.get(name) or "Helfärgad")
        return value if value in ALLOWED_PATTERNS else "Helfärgad"

    return {
        "found": found,
        "confidence": confidence,
        "reason": " ".join(str(payload.get("reason") or "").split())[:400],
        "home_pattern": pattern("home_pattern"),
        "home_color_1": _normalize_hex(payload.get("home_color_1"), "#111827"),
        "home_color_2": _normalize_hex(payload.get("home_color_2"), "#FFFFFF"),
        "away_pattern": pattern("away_pattern"),
        "away_color_1": _normalize_hex(payload.get("away_color_1"), "#FFFFFF"),
        "away_color_2": _normalize_hex(payload.get("away_color_2"), "#111827"),
        "sources": sources,
        "home_verified": home_verified,
        "away_verified": away_verified,
        "club_match": str(payload.get("club_match") or "uncertain")[:80],
    }


def likely_club_name(team_name):
    """Strip common youth/team suffixes without pretending we know the club identity."""
    text = " ".join(str(team_name or "").strip().split())
    if not text:
        return ""
    # Common Swedish/European youth labels and squad variants, usually at the end.
    suffix = re.compile(
        r"(?:\s+|[-_/])(?:P|F|U)?(?:19|20)?\d{1,2}|(?:\s+|[-_/])(?:Svart|Blå|Bla|Röd|Rod|Vit|Grön|Gron|Gul|Orange|1|2|3|4|A|B)\b",
        flags=re.I,
    )
    previous = None
    candidate = text
    while previous != candidate:
        previous = candidate
        candidate = suffix.sub("", candidate).strip(" -_/,")
        candidate = " ".join(candidate.split())
    return candidate or text


def _context_text(location="", country_code="", age_class="", search_hint=""):
    bits = []
    if str(location or "").strip():
        bits.append(f"cupens spelort: {str(location).strip()}")
    if str(country_code or "").strip():
        bits.append(f"land: {str(country_code).strip()}")
    if str(age_class or "").strip():
        bits.append(f"åldersklass: {str(age_class).strip()}")
    if str(search_hint or "").strip():
        bits.append(f"arrangörens sökledtråd: {str(search_hint).strip()}")
    return "; ".join(bits) or "ingen extra kontext"


def _search_strategies(clean_name, *, location="", country_code="", age_class="", search_hint=""):
    club_name = likely_club_name(clean_name)
    context = _context_text(location, country_code, age_class, search_hint)
    strategies = [
        (
            "Exakt lag + cupkontext",
            f"Sök först på hela lagnamnet '{clean_name}' tillsammans med relevant ort/åldersklass. Extra kontext: {context}.",
        )
    ]
    if club_name and club_name.casefold() != clean_name.casefold():
        strategies.append((
            "Klubbnamn utan ungdomssuffix",
            f"Första sökningen gav inget tillräckligt belagt. Sök nu på sannolikt klubbnamn '{club_name}' utan ungdoms-/truppsuffix och använd '{clean_name}' endast för att verifiera rätt lag. Extra kontext: {context}.",
        ))
    strategies.append((
        "Lokala och visuella källor",
        f"Bredda sökningen för '{clean_name}'. Leta särskilt på klubbens egen webbplats/webbshop, laget.se/Svenskalag eller motsvarande lagsida, distriktsförbund/cupsida och färska matchbilder eller matchreferat. Extra kontext: {context}. Bekräfta klubbidentiteten innan färger används.",
    ))
    # Keep cost bounded and avoid duplicate strategy text.
    unique = []
    seen = set()
    for label, instruction in strategies:
        key = instruction.casefold()
        if key not in seen:
            unique.append((label, instruction))
            seen.add(key)
    return unique[:MAX_SEARCH_ATTEMPTS]


def _schema():
    return {
        "type": "object",
        "properties": {
            "found": {"type": "boolean"},
            "confidence": {"type": "string", "enum": ALLOWED_CONFIDENCE},
            "reason": {"type": "string"},
            "home_pattern": {"type": "string", "enum": ALLOWED_PATTERNS},
            "home_color_1": {"type": "string"},
            "home_color_2": {"type": "string"},
            "away_pattern": {"type": "string", "enum": ALLOWED_PATTERNS},
            "away_color_1": {"type": "string"},
            "away_color_2": {"type": "string"},
            "sources": {"type": "array", "items": {"type": "string"}, "maxItems": MAX_SOURCES},
            "home_verified": {"type": "boolean"},
            "away_verified": {"type": "boolean"},
            "club_match": {"type": "string"},
        },
        "required": [
            "found", "confidence", "reason",
            "home_pattern", "home_color_1", "home_color_2",
            "away_pattern", "away_color_1", "away_color_2", "sources",
            "home_verified", "away_verified", "club_match",
        ],
        "additionalProperties": False,
    }


def _request_suggestion(clean_name, api_key, *, model, timeout_seconds, strategy_instruction, opener):
    instructions = (
        f"Du hjälper en svensk cuparrangör med Tröj setup för laget '{clean_name}'. {strategy_instruction} "
        "Ungdomslag är ofta lokala och dåligt dokumenterade och kan heta t.ex. P2014, F2013, U13, Svart, Blå, 1 eller 2 efter klubbnamnet. "
        "Behandla sådana delar som lag-/åldersetiketter, inte som en annan klubb. Gissa aldrig klubbidentitet. club_match ska kort ange vilken klubb du tror laget tillhör. "
        "Prioritera primärkällor, men en tydlig färsk bild från en trovärdig cup-/förbunds-/lagsida kan ge ett granskningsbart låg-säkerhetsförslag. "
        "Det är okej att hitta bara hemma- eller bortastället: sätt home_verified/away_verified separat. found=true får användas även vid low confidence "
        "om minst ett ställ är belagt av en faktisk källa. Om ett ställ inte kan beläggas ska dess *_verified vara false; hitta inte på färger. "
        "För verifierade ställ: ange praktiska HEX-färger (#RRGGBB) och närmast passande tillåtet mönster. reason ska kort förklara vad som är säkert/osäkert. "
        "Returnera upp till fem faktiska käll-URL:er. Inget av detta är facit; arrangören kommer att godkänna eller redigera innan något sparas."
    )
    body = {
        "model": model,
        "store": False,
        "input": [{"role": "user", "content": [{"type": "input_text", "text": instructions}]}],
        "tools": [{"type": "web_search"}],
        "text": {"format": {"type": "json_schema", "name": "cupnavi_kit_suggestion", "strict": True, "schema": _schema()}},
    }
    request = Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with opener(request, timeout=timeout_seconds) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise RuntimeError(f"AI-förslaget misslyckades: {exc}") from exc
    if response_payload.get("error"):
        error = response_payload["error"]
        message = error.get("message") if isinstance(error, dict) else error
        raise RuntimeError(f"AI-förslaget misslyckades: {message}")
    raw_text = _extract_output_text(response_payload)
    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        match = re.search(r"\{.*\}", raw_text, flags=re.S)
        if not match:
            raise ValueError("AI-svaret kunde inte tolkas som ett matchställ.") from exc
        parsed = json.loads(match.group(0))
    return normalize_kit_suggestion(parsed)


def _result_score(result):
    verified = int(bool(result.get("home_verified"))) + int(bool(result.get("away_verified")))
    confidence = {"low": 1, "medium": 2, "high": 3}.get(result.get("confidence"), 0)
    return (int(bool(result.get("found"))), verified, confidence, len(result.get("sources") or []))


def suggest_team_kit(
    team_name,
    api_key,
    *,
    model="gpt-5.6-luna",
    timeout_seconds=30,
    location="",
    country_code="",
    age_class="",
    search_hint="",
    opener=urlopen,
):
    """Try several bounded web-search strategies and return a cautious editable suggestion."""
    clean_name = " ".join(str(team_name or "").strip().split())
    if not clean_name:
        raise ValueError("Ange ett lagnamn först.")
    if not api_key:
        raise ValueError("Ingen AI-nyckel är konfigurerad.")

    strategies = _search_strategies(
        clean_name,
        location=location,
        country_code=country_code,
        age_class=age_class,
        search_hint=search_hint,
    )
    attempts = []
    best = None
    for label, strategy_instruction in strategies:
        result = _request_suggestion(
            clean_name,
            api_key,
            model=model,
            timeout_seconds=timeout_seconds,
            strategy_instruction=strategy_instruction,
            opener=opener,
        )
        attempts.append(label)
        result["search_strategy"] = label
        result["search_attempts"] = len(attempts)
        result["attempted_strategies"] = list(attempts)
        if best is None or _result_score(result) > _result_score(best):
            best = result
        # A grounded result is enough; don't spend more searches just to inflate confidence.
        if result.get("found"):
            return result

    best = best or normalize_kit_suggestion({})
    best["search_strategy"] = attempts[-1] if attempts else "Ingen"
    best["search_attempts"] = len(attempts)
    best["attempted_strategies"] = list(attempts)
    return best
