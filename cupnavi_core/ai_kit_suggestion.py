import json
import re
from urllib.request import Request, urlopen

ALLOWED_PATTERNS = ["Helfärgad", "Vertikala ränder", "Horisontella ränder", "Rutigt", "Delad"]
ALLOWED_CONFIDENCE = ["low", "medium", "high"]


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
    found = bool(payload.get("found")) and confidence in {"medium", "high"}

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
    }


def suggest_team_kit(
    team_name,
    api_key,
    *,
    model="gpt-5.6-luna",
    timeout_seconds=30,
    opener=urlopen,
):
    """Return a cautious kit suggestion from a team name.

    The model is instructed not to guess when the club cannot be identified with
    reasonable confidence. The result is only a starting suggestion for the
    organizer; it is never treated as authoritative kit data.
    """
    clean_name = " ".join(str(team_name or "").strip().split())
    if not clean_name:
        raise ValueError("Ange ett lagnamn först.")
    if not api_key:
        raise ValueError("Ingen AI-nyckel är konfigurerad.")

    schema = {
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
        },
        "required": [
            "found", "confidence", "reason",
            "home_pattern", "home_color_1", "home_color_2",
            "away_pattern", "away_color_1", "away_color_2",
        ],
        "additionalProperties": False,
    }
    instructions = (
        f"Du hjälper en cuparrangör ange matchställ för laget '{clean_name}'. "
        "Identifiera endast klubben om namnet rimligen pekar på en känd, specifik förening. "
        "Om namnet är tvetydigt, lokalt/okänt eller du inte är säker: found=false och confidence=low. "
        "Gissa inte. Om klubben kan identifieras: ange traditionellt/typiskt hemmaställ och ett vanligt "
        "bortaställ som en praktisk startpunkt, inte som garanti för aktuell säsong. "
        "Färger ska vara HEX (#RRGGBB). Mönstret måste vara ett av de tillåtna svenska värdena. "
        "Sätt found=true endast vid medium eller high confidence. reason ska kort förklara osäkerheten."
    )
    body = {
        "model": model,
        "store": False,
        "input": [{"role": "user", "content": [{"type": "input_text", "text": instructions}]}],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "cupnavi_kit_suggestion",
                "strict": True,
                "schema": schema,
            }
        },
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
