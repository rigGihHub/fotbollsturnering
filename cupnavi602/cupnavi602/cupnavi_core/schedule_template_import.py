import base64
import io
import json
import re
from urllib.request import Request, urlopen

ALLOWED_CONFIDENCE = ["low", "medium", "high"]


def _compact_image(image_bytes, mime_type, max_dimension=2000, jpeg_quality=88):
    try:
        from PIL import Image
        image = Image.open(io.BytesIO(image_bytes))
        image.load()
        if max(image.size) <= max_dimension:
            return image_bytes, mime_type
        image.thumbnail((max_dimension, max_dimension))
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")
        out = io.BytesIO()
        image.save(out, format="JPEG", quality=jpeg_quality, optimize=True)
        return out.getvalue(), "image/jpeg"
    except Exception:
        return image_bytes, mime_type


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


def _bounded_int(value, minimum, maximum, fallback):
    try:
        value = int(value)
    except (TypeError, ValueError):
        return fallback
    return max(minimum, min(maximum, value))


def normalize_schedule_template(payload):
    payload = payload or {}
    confidence = str(payload.get("confidence") or "low").lower()
    if confidence not in ALLOWED_CONFIDENCE:
        confidence = "low"
    return {
        "confidence": confidence,
        "summary": " ".join(str(payload.get("summary") or "").split())[:700],
        "group_count": _bounded_int(payload.get("group_count"), 0, 64, 0),
        "typical_group_size": _bounded_int(payload.get("typical_group_size"), 0, 64, 0),
        "pitch_count": _bounded_int(payload.get("pitch_count"), 0, 64, 0),
        "synchronized_pitch_times": bool(payload.get("synchronized_pitch_times")),
        "first_match_time": str(payload.get("first_match_time") or "")[:5],
        "last_match_time": str(payload.get("last_match_time") or "")[:5],
        "estimated_match_interval_minutes": _bounded_int(payload.get("estimated_match_interval_minutes"), 0, 240, 0),
        "estimated_min_team_rest_minutes": _bounded_int(payload.get("estimated_min_team_rest_minutes"), 0, 360, 0),
        "compactness": _bounded_int(payload.get("compactness"), 0, 100, 50),
        "playoff_present": bool(payload.get("playoff_present")),
        "caveats": [" ".join(str(item).split())[:300] for item in (payload.get("caveats") or []) if str(item).strip()][:8],
    }


def extract_schedule_template_from_image(
    image_bytes,
    mime_type,
    api_key,
    *,
    model="gpt-5.6-luna",
    timeout_seconds=60,
    opener=urlopen,
):
    """Read the *structure* of a previous tournament schedule from an image.

    It intentionally does not import old team names or results. The output is a
    proposed scheduling style that the organizer reviews before applying.
    """
    if not api_key:
        raise ValueError("Ingen AI-nyckel är konfigurerad.")
    if not image_bytes:
        raise ValueError("Bilden är tom.")
    if len(image_bytes) > 20 * 1024 * 1024:
        raise ValueError("Bilden är större än 20 MB.")

    compact, compact_mime = _compact_image(image_bytes, mime_type or "image/png")
    data_url = f"data:{compact_mime};base64,{base64.b64encode(compact).decode('ascii')}"

    schema = {
        "type": "object",
        "properties": {
            "confidence": {"type": "string", "enum": ALLOWED_CONFIDENCE},
            "summary": {"type": "string"},
            "group_count": {"type": "integer"},
            "typical_group_size": {"type": "integer"},
            "pitch_count": {"type": "integer"},
            "synchronized_pitch_times": {"type": "boolean"},
            "first_match_time": {"type": "string"},
            "last_match_time": {"type": "string"},
            "estimated_match_interval_minutes": {"type": "integer"},
            "estimated_min_team_rest_minutes": {"type": "integer"},
            "compactness": {"type": "integer"},
            "playoff_present": {"type": "boolean"},
            "caveats": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "confidence", "summary", "group_count", "typical_group_size", "pitch_count",
            "synchronized_pitch_times", "first_match_time", "last_match_time",
            "estimated_match_interval_minutes", "estimated_min_team_rest_minutes",
            "compactness", "playoff_present", "caveats",
        ],
        "additionalProperties": False,
    }
    instructions = (
        "Analysera bilden som ett tidigare cup- eller matchcampschema. Läs av själva upplägget, inte "
        "resultaten. Försök identifiera antal grupper, typisk gruppstorlek, antal planer, om planerna "
        "följer gemensamma avsparkstider, första/sista matchtid, ungefärligt intervall mellan starter, "
        "ungefärlig minsta vila mellan ett lags matcher, hur kompakt dagen är på skalan 0–100 och om "
        "slutspel verkar finnas. Gissa inte när bilden inte stödjer slutsatsen: använd 0/tom sträng och "
        "lägg osäkerheten i caveats. Teamnamn ska inte kopieras. summary ska beskriva strukturen på enkel svenska."
    )
    body = {
        "model": model,
        "store": False,
        "input": [{
            "role": "user",
            "content": [
                {"type": "input_text", "text": instructions},
                {"type": "input_image", "image_url": data_url, "detail": "high"},
            ],
        }],
        "text": {"format": {"type": "json_schema", "name": "cupnavi_schedule_template", "strict": True, "schema": schema}},
    }
    req = Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with opener(req, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise RuntimeError(f"AI-avläsningen misslyckades: {exc}") from exc
    if payload.get("error"):
        err = payload["error"]
        message = err.get("message") if isinstance(err, dict) else err
        raise RuntimeError(f"AI-avläsningen misslyckades: {message}")
    raw = _extract_output_text(payload)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        match = re.search(r"\{.*\}", raw, flags=re.S)
        if not match:
            raise ValueError("AI-svaret kunde inte tolkas som ett schemaupplägg.") from exc
        parsed = json.loads(match.group(0))
    return normalize_schedule_template(parsed)


def _balanced_group_sizes(team_count, group_count):
    team_count = max(0, int(team_count or 0))
    group_count = max(1, min(team_count or 1, int(group_count or 1)))
    base, remainder = divmod(team_count, group_count)
    return [base + (1 if index < remainder else 0) for index in range(group_count)]


def adapt_schedule_template(
    template,
    *,
    team_count,
    pitch_count,
    current_match_duration_minutes,
    current_min_rest_minutes=0,
):
    """Translate an old schedule style to the current tournament.

    The old schedule is inspiration, not a literal import. Team count and pitch
    count always come from the current tournament.
    """
    template = normalize_schedule_template(template)
    teams = max(2, int(team_count or 0))
    pitches = max(1, int(pitch_count or 1))
    match_duration = max(1, int(current_match_duration_minutes or 1))

    typical_size = int(template.get("typical_group_size") or 0)
    original_groups = int(template.get("group_count") or 0)
    if typical_size >= 2:
        group_count = max(1, round(teams / typical_size))
    elif original_groups >= 1:
        group_count = min(teams, original_groups)
    else:
        group_count = max(1, round(teams / 4))
    group_count = max(1, min(teams // 2 if teams >= 2 else 1, group_count))
    sizes = _balanced_group_sizes(teams, group_count)

    group_matches = sum(size * (size - 1) // 2 for size in sizes)
    playoff_matches = 0
    if template.get("playoff_present") and teams >= 4:
        possible = min(teams, max(4, group_count * 2))
        playoff_size = next((size for size in (16, 8, 4) if size <= possible), 4)
        playoff_matches = max(0, playoff_size - 1)
    total_matches = group_matches + playoff_matches

    observed_interval = int(template.get("estimated_match_interval_minutes") or 0)
    slot_minutes = max(match_duration, observed_interval) if observed_interval else match_duration
    waves = (total_matches + pitches - 1) // pitches
    estimated_day_minutes = max(0, waves * slot_minutes)

    imported_rest = int(template.get("estimated_min_team_rest_minutes") or 0)
    min_rest = imported_rest if imported_rest > 0 else max(0, int(current_min_rest_minutes or 0))

    # Similarity describes how much of the *style* can be retained. A different
    # pitch count or highly different participant count naturally forces adaptation.
    similarity = 100
    old_pitches = int(template.get("pitch_count") or 0)
    if old_pitches and old_pitches != pitches:
        similarity -= min(25, abs(old_pitches - pitches) * 8)
    if typical_size and any(abs(size - typical_size) > 1 for size in sizes):
        similarity -= 15
    if template.get("confidence") == "medium":
        similarity -= 10
    elif template.get("confidence") == "low":
        similarity -= 30
    similarity = max(0, min(100, similarity))

    return {
        "team_count": teams,
        "pitch_count": pitches,
        "group_count": group_count,
        "group_sizes": sizes,
        "group_matches": group_matches,
        "playoff_matches": playoff_matches,
        "total_matches": total_matches,
        "synchronized_pitch_times": bool(template.get("synchronized_pitch_times")),
        "compactness": int(template.get("compactness") or 50),
        "minimum_team_rest_minutes": min_rest,
        "first_match_time": template.get("first_match_time") or "",
        "slot_minutes": slot_minutes,
        "estimated_day_minutes": estimated_day_minutes,
        "similarity": similarity,
        "similarity_label": (
            "Mycket likt originalet" if similarity >= 85 else
            "Tydligt inspirerat av originalet" if similarity >= 65 else
            "Kraftigt anpassat till den nya cupen"
        ),
    }
