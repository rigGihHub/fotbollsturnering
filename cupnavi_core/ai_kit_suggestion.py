import json
import re
import time
from threading import Lock
from urllib.request import Request, urlopen

ALLOWED_PATTERNS = ["Helfärgad", "Vertikala ränder", "Horisontella ränder", "Rutigt", "Delad", "Diagonala ränder", "Grafiskt"]
ALLOWED_CONFIDENCE = ["low", "medium", "high"]
ALLOWED_IDENTITY_STATUS = ["exact", "likely", "ambiguous", "unknown"]
MAX_SOURCES = 6
MAX_SEARCH_ATTEMPTS = 2
CACHE_TTL_SECONDS = 60 * 60 * 12
SEARCH_VERSION = "v673-pattern-first-assets"
ALLOWED_SEARCH_FOCUS = {"kit", "logo", "all"}

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


def _candidate_matches(values):
    out = []
    seen = set()
    for item in values or []:
        if not isinstance(item, dict):
            continue
        name = " ".join(str(item.get("name") or "").split())[:120]
        location = " ".join(str(item.get("location") or "").split())[:120]
        country = " ".join(str(item.get("country") or "").split())[:80]
        source_url = str(item.get("source_url") or "").strip()
        reason = " ".join(str(item.get("reason") or "").split())[:220]
        confidence = str(item.get("confidence") or "low").lower()
        if confidence not in ALLOWED_CONFIDENCE:
            confidence = "low"
        if not name or not source_url.startswith(("http://", "https://")):
            continue
        key = (name.casefold(), location.casefold(), source_url)
        if key in seen:
            continue
        seen.add(key)
        out.append({
            "name": name,
            "location": location,
            "country": country,
            "source_url": source_url,
            "reason": reason,
            "confidence": confidence,
        })
        if len(out) >= 4:
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
    identity_status = str(payload.get("identity_status") or "unknown").lower()
    if identity_status not in ALLOWED_IDENTITY_STATUS:
        identity_status = "unknown"
    candidate_matches = _candidate_matches(payload.get("candidate_matches") or [])
    logo_url = str(payload.get("logo_url") or "").strip()
    logo_source_url = str(payload.get("logo_source_url") or "").strip()
    logo_verified = bool(payload.get("logo_verified")) and logo_url.startswith("https://") and logo_source_url.startswith(("http://", "https://"))
    if identity_status in {"ambiguous", "unknown"}:
        logo_verified = False

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

    # Never mix shirt evidence across several plausible clubs. If identity is
    # ambiguous, stop before presenting colors and let the organiser choose.
    if identity_status in {"ambiguous", "unknown"} and candidate_matches:
        home_verified = False
        away_verified = False
        found = False

    # Confidence may not outrun the evidence. One source for one shirt is useful,
    # but it is not high-confidence consensus.
    kit_source_count = len(set(home_sources + away_sources))
    if found and confidence == "high" and kit_source_count < 2:
        confidence = "medium"
    if found and confidence == "medium" and kit_source_count < 1:
        confidence = "low"

    def pattern(name):
        raw = " ".join(str(payload.get(name) or "").strip().lower().replace("_", " ").replace("-", " ").split())
        aliases = {
            "helfärgad": "Helfärgad", "enfärgad": "Helfärgad", "solid": "Helfärgad", "plain": "Helfärgad",
            "vertikala ränder": "Vertikala ränder", "vertical stripes": "Vertikala ränder", "vertical striped": "Vertikala ränder", "striped": "Vertikala ränder", "stripes": "Vertikala ränder",
            "horisontella ränder": "Horisontella ränder", "horizontal stripes": "Horisontella ränder", "horizontal striped": "Horisontella ränder", "hoops": "Horisontella ränder", "hooped": "Horisontella ränder",
            "rutigt": "Rutigt", "checkered": "Rutigt", "checked": "Rutigt", "checkerboard": "Rutigt",
            "delad": "Delad", "split": "Delad", "halves": "Delad", "half and half": "Delad",
            "diagonala ränder": "Diagonala ränder", "diagonal stripes": "Diagonala ränder", "diagonal striped": "Diagonala ränder",
            "grafiskt": "Grafiskt", "graphic": "Grafiskt", "geometric": "Grafiskt", "gradient": "Grafiskt", "chevron": "Grafiskt", "camo": "Grafiskt",
        }
        if raw in aliases:
            return aliases[raw]
        exact = next((value for value in ALLOWED_PATTERNS if value.lower() == raw), None)
        if exact:
            return exact
        # Unknown pattern language is uncertainty, not evidence that the shirt is plain.
        return "Grafiskt" if raw else "Helfärgad"

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
        "identity_status": identity_status,
        "candidate_matches": candidate_matches,
        "logo_url": logo_url if logo_verified else "",
        "logo_source_url": logo_source_url if logo_verified else "",
        "logo_verified": logo_verified,
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


def _context_text(location="", country_code="", age_class="", search_hint="", resolved_club="", resolved_source_url=""):
    bits = []
    if str(location or "").strip():
        bits.append(f"cupens spelort: {str(location).strip()}")
    if str(country_code or "").strip():
        bits.append(f"land: {str(country_code).strip()}")
    if str(age_class or "").strip():
        bits.append(f"åldersklass: {str(age_class).strip()}")
    if str(search_hint or "").strip():
        bits.append(f"arrangörens sökledtråd: {str(search_hint).strip()}")
    if str(resolved_club or "").strip():
        bits.append(f"arrangören har valt klubbidentitet: {str(resolved_club).strip()}")
    if str(resolved_source_url or "").strip():
        bits.append(f"vald identitetskälla: {str(resolved_source_url).strip()}")
    return "; ".join(bits) or "ingen extra kontext"


def _search_strategies(clean_name, *, location="", country_code="", age_class="", search_hint="", resolved_club="", resolved_source_url="", search_focus="kit"):
    """Two strong passes instead of three narrow sequential passes.

    The Responses web-search tool can perform several searches inside one call,
    so the first pass explicitly asks for a multi-query evidence sweep. Most
    teams should complete after this single network roundtrip.
    """
    club_name = likely_club_name(clean_name)
    context = _context_text(location, country_code, age_class, search_hint, resolved_club, resolved_source_url)
    focus = "klubbens officiella klubbmärke/logotyp" if search_focus == "logo" else "aktuella hemma- och bortaställ"
    primary = (
        "Identifiera klubben först och sök därefter efter rätt tillgång. Gör flera sökfrågor i samma omgång: "
        f"(1) exakt lag '{clean_name}', (2) sannolikt klubbnamn '{club_name}', "
        f"(3) officiell webbplats eller förbundsprofil och (4) {focus}. "
        f"Kontext: {context}. Cupens spelort är bara var turneringen hålls och får ALDRIG användas som belägg för klubbens hemort. "
        "Jämför klubbnamn, ort, webbdomän och emblem innan identiteten godkänns. Prioritera officiella källor och senaste relevanta säsongen. "
        "Källan måste visa själva tröjan eller uttryckligen beskriva stället; klubbens färger utan tröjbild är inte bevis. "
        "För hemma- respektive bortaställ ska separata källor anges; en allmän klubbsida räcker inte som tröjbevis."
    )
    fallback = (
        f"Första sökningen för '{clean_name}' var ofullständig. Fyll endast luckorna för {focus}. "
        f"Sök på '{club_name}' och den identifierade officiella domänen. Kontext: {context}. "
        "För matchställ: använd officiell webbshop, materialpartner, aktuell lagbild eller färsk matchbild. Sök även i offentliga, verifierbara Instagram- och Facebook-inlägg från klubbens eller lagets officiella konto. "
        "Sociala medier får bara verifiera ett ställ när två aktuella bilder är samstämmiga, eller när en social bild bekräftas av en officiell klubb-, förbunds- eller materialpartnerkälla. Konton/inlägg som kräver inloggning är inte bevis. "
        "För klubbmärke: kräv att bilden kommer från officiell klubbdomän, förbundsprofil eller Wikimedia med tydlig klubbkoppling. "
        "Acceptera en verifierad delträff hellre än att gissa."
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
            "identity_status": {"type": "string", "enum": ALLOWED_IDENTITY_STATUS},
            "logo_url": {"type": "string"},
            "logo_source_url": {"type": "string"},
            "logo_verified": {"type": "boolean"},
            "candidate_matches": {
                "type": "array",
                "maxItems": 4,
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "location": {"type": "string"},
                        "country": {"type": "string"},
                        "source_url": {"type": "string"},
                        "reason": {"type": "string"},
                        "confidence": {"type": "string", "enum": ALLOWED_CONFIDENCE},
                    },
                    "required": ["name", "location", "country", "source_url", "reason", "confidence"],
                    "additionalProperties": False,
                },
            },
        },
        "required": [
            "found", "confidence", "reason",
            "home_pattern", "home_color_1", "home_color_2",
            "away_pattern", "away_color_1", "away_color_2",
            "home_sources", "away_sources", "home_evidence", "away_evidence", "sources",
            "home_verified", "away_verified", "club_match", "identity_status", "candidate_matches",
            "logo_url", "logo_source_url", "logo_verified",
        ],
        "additionalProperties": False,
    }


def _request_suggestion(clean_name, api_key, *, model, timeout_seconds, strategy_instruction, search_focus, opener):
    instructions = (
        f"Du hjälper en svensk cuparrangör att hitta klubbuppgifter för laget '{clean_name}'. Sökfokus: {search_focus}. {strategy_instruction} "
        "Ungdomslag kan heta P2014, F2013, U13, Svart, Blå, 1 eller 2 efter klubbnamnet; det är ofta lagetiketter och inte en annan klubb. "
        "Gissa aldrig klubbidentitet. club_match ska säga vilken klubb/ort som faktiskt matchades. "
        "Sätt identity_status=exact när identiteten är tydligt belagd, likely när en kandidat klart dominerar, ambiguous när flera klubbar/lag är rimliga och unknown när ingen kan beläggas. "
        "Vid ambiguous: returnera 2–4 candidate_matches med namn, ort, land, en identitetskälla och kort skäl. Blanda då aldrig tröjkällor mellan kandidater och sätt home_verified/away_verified=false. "
        "Om arrangören har valt en klubbidentitet i kontexten ska den identiteten användas och inte ifrågasättas annat än vid uppenbar källkonflikt. "
        "VIKTIGT FÖR KORREKTHET: home_verified får bara vara true om minst en URL i home_sources faktiskt stöder hemmaställets färg/mönster. "
        "away_verified får bara vara true om minst en URL i away_sources faktiskt stöder bortastället. Samma källa får användas för båda bara om den tydligt visar båda. "
        "Skriv i home_evidence/away_evidence vad källan visar. Prioritera officiell klubb/webbshop, sedan förbund/cup/lagplattform, därefter färska matchbilder. Kontrollera att källan faktiskt visar tröjan eller uttryckligen beskriver stället; klubbens färger, arena, flagga eller en logotypbild räknas inte som tröjbevis. Läs bildtext, alt-text och sidans säsong/uppdateringsdatum och välj den senaste relevanta säsongen. Offentliga inlägg från klubbens officiella Instagram eller Facebook får användas som kompletterande bildbevis, men aldrig ett ensamt gammalt eller odaterat inlägg. "
        "Om flera trovärdiga källor motsäger varandra, välj den nyaste relevanta säsongen och sänk confidence. "
        "Det är bättre att returnera bara ett belagt hemmaställ än att fylla i ett osäkert bortaställ. "
        "För verifierade ställ: analysera TRÖJANS GEOMETRI separat från klubbfärgerna. Avgör först om tyget visuellt är enfärgat, vertikalrandigt, horisontalrandigt, rutigt, delat, diagonalrandigt eller grafiskt. Välj Helfärgad endast när den verifierade tröjbilden verkligen saknar ett tydligt återkommande mönster; två eller fler tydliga kontrasterande vertikala band ska ge Vertikala ränder och motsvarande horisontella band Horisontella ränder. Logotyp, sponsortryck, krage och ärmkanter är inte ett tröjmönster. Skriv i home_evidence/away_evidence vilket visuellt kännetecken som motiverar mönstret. Ange därefter praktiska HEX-färger (#RRGGBB) utifrån själva tröjan, inte färgnamn från klubbens profil. Beskriv huvudfärg först och den tydliga kontrastfärgen därefter. Välj närmast passande mönster bland Helfärgad, Vertikala ränder, Horisontella ränder, Rutigt, Delad, Diagonala ränder eller Grafiskt; välj Grafiskt när designen är chevron, camo, gradient eller annan tydlig grafik och gissa inte ränder. "
        "Hitta även klubbens officiella logotyp. logo_url måste vara en direkt HTTPS-bildadress och logo_source_url sidan som belägger att märket tillhör rätt klubb. Sätt logo_verified=true endast när klubbidentiteten och bilden är tydliga. "
        "Om sökfokus är logo ska logotypen prioriteras och osökta matchställ lämnas overifierade. Om sökfokus är kit ska matchställen prioriteras; logotyp får bara följa med när den hittas på samma verifierade klubbkälla. "
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
    identity = {"unknown": 0, "ambiguous": 0, "likely": 1, "exact": 2}.get(result.get("identity_status"), 0)
    return (identity, int(bool(result.get("found"))), verified, int(bool(result.get("logo_verified"))), confidence, kit_sources)


def _identity_key(result):
    return " ".join(str(result.get("club_match") or "").casefold().split())


def _identities_compatible(first_key, second_key):
    """Allow naming suffixes, but never merge two same-named clubs from different places."""
    if not first_key or not second_key:
        return False
    if first_key == second_key:
        return True
    generic = {"if", "ff", "fk", "ik", "fotboll", "football", "club", "förening", "forening"}
    first_tokens, second_tokens = set(first_key.split()), set(second_key.split())
    shared = first_tokens & second_tokens
    extra = (first_tokens | second_tokens) - shared
    return len(shared) >= 2 and extra <= generic


def _merge_compatible_results(first, second):
    """Keep complementary evidence only when both passes identify the same club.

    A second search must never splice another club's badge into the first club's
    kit. Exact selected-source retries are compatible even if naming differs.
    """
    if not first:
        return dict(second or {})
    if not second:
        return dict(first)
    first_key, second_key = _identity_key(first), _identity_key(second)
    compatible = _identities_compatible(first_key, second_key)
    if not compatible:
        return dict(max((first, second), key=_result_score))

    first_is_preferred = _result_score(first) >= _result_score(second)
    preferred = dict(first if first_is_preferred else second)
    other = second if first_is_preferred else first
    for prefix in ("home", "away"):
        if not preferred.get(f"{prefix}_verified") and other.get(f"{prefix}_verified"):
            for suffix in ("verified", "pattern", "color_1", "color_2", "sources", "evidence"):
                preferred[f"{prefix}_{suffix}"] = other.get(f"{prefix}_{suffix}")
    if not preferred.get("logo_verified") and other.get("logo_verified"):
        for key in ("logo_verified", "logo_url", "logo_source_url"):
            preferred[key] = other.get(key)
    preferred["sources"] = _urls((preferred.get("sources") or []) + (other.get("sources") or []))
    preferred["found"] = bool(preferred.get("home_verified") or preferred.get("away_verified"))
    return preferred


def _cache_key(clean_name, location, country_code, age_class, search_hint, model, resolved_club="", resolved_source_url="", search_focus="kit"):
    return "|".join(
        " ".join(str(value or "").casefold().split())
        for value in (SEARCH_VERSION, likely_club_name(clean_name), clean_name, location, country_code, age_class, search_hint, model, resolved_club, resolved_source_url, search_focus)
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
    model="gpt-4.1-mini",
    timeout_seconds=22,
    location="",
    country_code="",
    age_class="",
    search_hint="",
    resolved_club="",
    resolved_source_url="",
    search_focus="kit",
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
    search_focus = str(search_focus or "kit").strip().lower()
    if search_focus not in ALLOWED_SEARCH_FOCUS:
        raise ValueError("Okänt sökfokus.")

    cache_key = _cache_key(clean_name, location, country_code, age_class, search_hint, model, resolved_club, resolved_source_url, search_focus)
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
        resolved_club=resolved_club,
        resolved_source_url=resolved_source_url,
        search_focus=search_focus,
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
            search_focus=search_focus,
            opener=opener,
        )
        attempts.append(label)
        result["search_strategy"] = label
        result["search_attempts"] = len(attempts)
        result["attempted_strategies"] = list(attempts)
        result["cache_hit"] = False
        best = _merge_compatible_results(best, result)

        # Stop after the fast first pass when the evidence is already useful.
        both_verified = bool(best.get("home_verified") and best.get("away_verified"))
        exact_logo = bool(best.get("identity_status") == "exact" and best.get("logo_verified"))
        if index == 0 and ((search_focus == "logo" and exact_logo) or (search_focus != "logo" and both_verified and best.get("identity_status") == "exact")):
            break

    best = best or normalize_kit_suggestion({})
    best["search_strategy"] = attempts[-1] if attempts else "Ingen"
    best["search_attempts"] = len(attempts)
    best["attempted_strategies"] = list(attempts)
    best["cache_hit"] = False
    if use_cache and opener is urlopen and best.get("found"):
        _cache_put(cache_key, best)
    return best
