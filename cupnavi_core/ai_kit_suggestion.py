import json
import re
import time
from threading import Lock
from urllib.request import Request, urlopen

ALLOWED_PATTERNS = ["Helfärgad", "Vertikala ränder", "Horisontella ränder", "Rutigt", "Delad"]
ALLOWED_CONFIDENCE = ["low", "medium", "high"]
MAX_SOURCES = 6
MAX_SEARCH_ATTEMPTS = 2
CACHE_TTL_SECONDS = 60 * 60 * 12

# Process-local cache: Streamlit reruns keep the Python process alive. A repeated
# search for the same club therefore returns immediately without a new web call.
_KIT_CACHE = {}
_KIT_CACHE_LOCK = Lock()


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


def _urls(values):
    out = []
    for value in values or []:
        url = str(value or "").strip()
        if url.startswith(("http://", "https://")) and url not in out:
            out.append(url)
        if len(out) >= MAX_SOURCES:
            break
    return out


def normalize_kit_suggestion(payload):
    """Normalize and *tighten* AI output.

    v601 deliberately does not trust a model's verified boolean on its own.
    A home/away kit is only treated as verified when that specific kit has at
    least one source URL. This prevents an unrelated general club source from
    accidentally validating both shirts.
    """
    payload = payload or {}
    confidence = str(payload.get("confidence") or "low").lower()
    if confidence not in ALLOWED_CONFIDENCE:
        confidence = "low"

    home_sources = _urls(payload.get("home_sources") or [])
    away_sources = _urls(payload.get("away_sources") or [])
    legacy_sources = _urls(payload.get("sources") or [])

    # Backward compatibility for old/fake payloads used by older tests.
    if not home_sources and bool(payload.get("home_verified")) and legacy_sources:
        home_sources = legacy_sources[:1]
    if not away_sources and bool(payload.get("away_verified")) and legacy_sources:
        away_sources = legacy_sources[:1]

    home_verified = bool(payload.get("home_verified")) and bool(home_sources)
    away_verified = bool(payload.get("away_verified")) and bool(away_sources)
    sources = _urls(home_sources + away_sources + legacy_sources)
    found = bool(payload.get("found")) and (home_verified or away_verified)

    # Confidence may not outrun the evidence. One source for one shirt is useful,
    # but it is not high-confidence consensus.
    kit_source_count = len(set(home_sources + away_sources))
    if found and confidence == "high" and kit_source_count < 2:
        confidence = "medium"
    if found and confidence == "medium" and kit_source_count < 1:
        confidence = "low"

    def pattern(name):
        value = str(payload.get(name) or "Helfärgad")
        return value if value in ALLOWED_PATTERNS else "Helfärgad"

    return {
        "found": found,
        "confidence": confidence,
        "reason": " ".join(str(payload.get("reason") or "").split())[:500],
        "home_pattern": pattern("home_pattern"),
        "home_color_1": _normalize_hex(payload.get("home_color_1"), "#111827"),
        "home_color_2": _normalize_hex(payload.get("home_color_2"), "#FFFFFF"),
        "away_pattern": pattern("away_pattern"),
        "away_color_1": _normalize_hex(payload.get("away_color_1"), "#FFFFFF"),
        "away_color_2": _normalize_hex(payload.get("away_color_2"), "#111827"),
        "sources": sources,
        "home_sources": home_sources,
        "away_sources": away_sources,
        "home_evidence": " ".join(str(payload.get("home_evidence") or "").split())[:300],
        "away_evidence": " ".join(str(payload.get("away_evidence") or "").split())[:300],
        "home_verified": home_verified,
        "away_verified": away_verified,
        "club_match": " ".join(str(payload.get("club_match") or "uncertain").split())[:120],
    }


def likely_club_name(team_name):
    """Strip common youth/team suffixes without pretending we know the club identity."""
    text = " ".join(str(team_name or "").strip().split())
    if not text:
        return ""
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
    """Two strong passes instead of three narrow sequential passes.

    The Responses web-search tool can perform several searches inside one call,
    so the first pass explicitly asks for a multi-query evidence sweep. Most
    teams should complete after this single network roundtrip.
    """
    club_name = likely_club_name(clean_name)
    context = _context_text(location, country_code, age_class, search_hint)
    primary = (
        "Gör en snabb evidenssökning i flera spår i samma sökomgång: "
        f"(1) exakt lag '{clean_name}', (2) sannolikt klubbnamn '{club_name}', "
        "(3) klubbens officiella webbplats/webbshop och (4) trovärdig lagsida/cupsida/förbundssida med aktuell bild eller text. "
        f"Kontext: {context}. Prioritera den aktuella säsongen och kontrollera att källorna faktiskt avser rätt klubb. "
        "För hemma- respektive bortaställ ska du ange separata källor; en allmän klubbsida räcker inte som bevis för båda."
    )
    fallback = (
        f"Första evidenssökningen för '{clean_name}' var ofullständig. Fyll endast luckorna. "
        f"Sök på '{club_name}' + matchställ/tröja/kit/home/away tillsammans med relevant ort eller land. Kontext: {context}. "
        "Leta även i färska matchbilder, lagpresentationer, cupsidor och officiella sociala/webb-källor. "
        "Acceptera hellre ett verifierat hemmaställ än att gissa ett bortaställ."
    )
    return [("Snabb multikällesökning", primary), ("Riktad lucksökning", fallback)]


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
            "home_sources": {"type": "array", "items": {"type": "string"}, "maxItems": 4},
            "away_sources": {"type": "array", "items": {"type": "string"}, "maxItems": 4},
            "home_evidence": {"type": "string"},
            "away_evidence": {"type": "string"},
            "sources": {"type": "array", "items": {"type": "string"}, "maxItems": MAX_SOURCES},
            "home_verified": {"type": "boolean"},
            "away_verified": {"type": "boolean"},
            "club_match": {"type": "string"},
        },
        "required": [
            "found", "confidence", "reason",
            "home_pattern", "home_color_1", "home_color_2",
            "away_pattern", "away_color_1", "away_color_2",
            "home_sources", "away_sources", "home_evidence", "away_evidence", "sources",
            "home_verified", "away_verified", "club_match",
        ],
        "additionalProperties": False,
    }


def _request_suggestion(clean_name, api_key, *, model, timeout_seconds, strategy_instruction, opener):
    instructions = (
        f"Du hjälper en svensk cuparrangör att hitta matchställ för laget '{clean_name}'. {strategy_instruction} "
        "Ungdomslag kan heta P2014, F2013, U13, Svart, Blå, 1 eller 2 efter klubbnamnet; det är ofta lagetiketter och inte en annan klubb. "
        "Gissa aldrig klubbidentitet. club_match ska säga vilken klubb/ort som faktiskt matchades. "
        "VIKTIGT FÖR KORREKTHET: home_verified får bara vara true om minst en URL i home_sources faktiskt stöder hemmaställets färg/mönster. "
        "away_verified får bara vara true om minst en URL i away_sources faktiskt stöder bortastället. Samma källa får användas för båda bara om den tydligt visar båda. "
        "Skriv i home_evidence/away_evidence vad källan visar. Prioritera officiell klubb/webbshop, sedan förbund/cup/lagplattform, därefter färska matchbilder. "
        "Om flera trovärdiga källor motsäger varandra, välj den nyaste relevanta säsongen och sänk confidence. "
        "Det är bättre att returnera bara ett belagt hemmaställ än att fylla i ett osäkert bortaställ. "
        "För verifierade ställ: ange praktiska HEX-färger (#RRGGBB) och närmast passande tillåtet mönster. "
        "sources ska vara unionen av de viktigaste källorna. Inget sparas automatiskt; arrangören granskar förslaget."
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
    kit_sources = len(set((result.get("home_sources") or []) + (result.get("away_sources") or [])))
    return (int(bool(result.get("found"))), verified, confidence, kit_sources)


def _cache_key(clean_name, location, country_code, age_class, search_hint, model):
    return "|".join(
        " ".join(str(value or "").casefold().split())
        for value in (likely_club_name(clean_name), clean_name, location, country_code, age_class, search_hint, model)
    )


def _cache_get(key):
    now = time.time()
    with _KIT_CACHE_LOCK:
        item = _KIT_CACHE.get(key)
        if not item:
            return None
        created_at, value = item
        if now - created_at > CACHE_TTL_SECONDS:
            _KIT_CACHE.pop(key, None)
            return None
        return dict(value)


def _cache_put(key, value):
    with _KIT_CACHE_LOCK:
        _KIT_CACHE[key] = (time.time(), dict(value))


def suggest_team_kit(
    team_name,
    api_key,
    *,
    model="gpt-5.6-luna",
    timeout_seconds=22,
    location="",
    country_code="",
    age_class="",
    search_hint="",
    opener=urlopen,
    use_cache=True,
):
    """Fast, evidence-aware kit search.

    Typical path = one web-search roundtrip. A second targeted request is only
    used if the first pass found nothing or only weak/partial evidence.
    """
    clean_name = " ".join(str(team_name or "").strip().split())
    if not clean_name:
        raise ValueError("Ange ett lagnamn först.")
    if not api_key:
        raise ValueError("Ingen AI-nyckel är konfigurerad.")

    cache_key = _cache_key(clean_name, location, country_code, age_class, search_hint, model)
    if use_cache and opener is urlopen:
        cached = _cache_get(cache_key)
        if cached:
            cached["cache_hit"] = True
            cached["search_strategy"] = "Snabbcache"
            cached["search_attempts"] = 0
            cached["attempted_strategies"] = []
            return cached

    strategies = _search_strategies(
        clean_name,
        location=location,
        country_code=country_code,
        age_class=age_class,
        search_hint=search_hint,
    )[:MAX_SEARCH_ATTEMPTS]
    attempts = []
    best = None
    for index, (label, strategy_instruction) in enumerate(strategies):
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
        result["cache_hit"] = False
        if best is None or _result_score(result) > _result_score(best):
            best = result

        # Stop after the fast first pass when the evidence is already useful.
        both_verified = bool(result.get("home_verified") and result.get("away_verified"))
        good_single = bool(result.get("found") and result.get("confidence") in {"medium", "high"})
        if index == 0 and (both_verified or good_single):
            break

    best = best or normalize_kit_suggestion({})
    best["search_strategy"] = attempts[-1] if attempts else "Ingen"
    best["search_attempts"] = len(attempts)
    best["attempted_strategies"] = list(attempts)
    best["cache_hit"] = False
    if use_cache and opener is urlopen and best.get("found"):
        _cache_put(cache_key, best)
    return best
