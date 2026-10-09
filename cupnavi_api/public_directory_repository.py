"""Small, read-only directory of published arrangements for the public homepage."""
from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from .repository import _dict_rows, connect


def _date(value) -> date | None:
    try:
        return date.fromisoformat(str(value or "").strip())
    except ValueError:
        return None


def public_cup_directory(*, today: date | None = None):
    today = today or datetime.now(ZoneInfo("Europe/Stockholm")).date()
    with connect() as con:
        columns = {row["name"] for row in _dict_rows(con.execute("PRAGMA table_info(tournaments)"))}
        optional = [name if name in columns else f"NULL AS {name}"
                    for name in ("arrangement_type", "arena_address")]
        lifecycle = " AND COALESCE(lifecycle_status,'draft') NOT IN ('trashed','purged')" if "lifecycle_status" in columns else ""
        rows = _dict_rows(con.execute(
            "SELECT id,name,public_slug,start_date,end_date," + ",".join(optional)
            + " FROM tournaments WHERE is_published=1" + lifecycle
        ))

    cups = []
    for row in rows:
        start, end = _date(row.get("start_date")), _date(row.get("end_date"))
        start = start or end
        end = max(start, end or start) if start else None
        status = "undated" if not start else "upcoming" if today < start else "completed" if today > end else "ongoing"
        cups.append({
            "id": row["id"], "name": row["name"], "public_slug": row["public_slug"],
            "start_date": start.isoformat() if start else None,
            "end_date": end.isoformat() if end else None,
            "arrangement_type": row["arrangement_type"], "arena_address": row["arena_address"],
            "status": status,
        })
    order = {"ongoing": 0, "upcoming": 1, "completed": 2, "undated": 3}
    cups.sort(key=lambda cup: (
        order[cup["status"]],
        -date.fromisoformat(cup["end_date"]).toordinal() if cup["status"] == "completed"
        else date.fromisoformat(cup["start_date"]).toordinal() if cup["start_date"] else 0,
        str(cup["name"]).casefold(), cup["id"],
    ))
    return {"cups": cups, "as_of": today.isoformat()}
