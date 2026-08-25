"""Ren schemalogik utan databas eller Streamlit."""

from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True)
class ScheduleWindow:
    start: datetime
    end_date: object
    latest_pitch_time: object
    group_match_duration: timedelta
    playoff_extra_minutes: int

    def duration_for_stage(self, stage):
        extra = self.playoff_extra_minutes if stage != "Gruppspel" else 0
        return self.group_match_duration + timedelta(minutes=extra)


def build_schedule_window(tournament, rules):
    cup_start_date = tournament.get("start_date") or tournament.get("tournament_date")
    cup_end_date = tournament.get("end_date") or cup_start_date
    if not cup_start_date or not cup_end_date:
        raise ValueError("Cupdatum saknas.")

    start = datetime.fromisoformat(f"{cup_start_date}T{rules['first_match_time']}")
    end_date = datetime.fromisoformat(cup_end_date).date()
    latest_pitch_time = datetime.strptime(
        rules["latest_kickoff_time"], "%H:%M"
    ).time()

    halves = int(rules["halves"])
    minutes_per_half = int(rules["minutes_per_half"])
    halftime_minutes = int(rules["halftime_minutes"])
    if halves < 1 or minutes_per_half < 1 or halftime_minutes < 0:
        raise ValueError("Matchtiderna är ogiltiga.")

    duration = timedelta(
        minutes=(halves * minutes_per_half)
        + ((halves - 1) * halftime_minutes)
    )
    extra = (
        int(tournament.get("extra_time_minutes") or 0)
        if tournament.get("playoff_tie_rule", "") == "Förlängning + straffar"
        else 0
    )
    if extra < 0:
        raise ValueError("Förlängningstiden är ogiltig.")

    return ScheduleWindow(
        start=start,
        end_date=end_date,
        latest_pitch_time=latest_pitch_time,
        group_match_duration=duration,
        playoff_extra_minutes=extra,
    )


def schedule_source_team_id(source):
    if not source or not isinstance(source, str):
        return None
    if not source.startswith("team:"):
        return None
    try:
        return int(source.split(":", 1)[1])
    except (TypeError, ValueError):
        return None
