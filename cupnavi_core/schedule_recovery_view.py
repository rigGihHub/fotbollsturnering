"""Presentation for ranked schedule recovery suggestions.

Persistence-sensitive recovery actions stay injected from app.py.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class ScheduleRecoveryDependencies:
    st: Any
    apply_extend: Callable[..., Any]
    apply_late_first: Callable[..., Any]
    apply_break: Callable[..., Any]
    apply_pitch: Callable[..., Any]


def render_schedule_recovery_actions(tournament_id, tournament, rules, context, *, deps: ScheduleRecoveryDependencies):
    st = deps.st
    if not context or int(context.get("unresolved", 0) or 0) <= 0:
        return

    unresolved = int(context.get("unresolved", 0) or 0)
    st.markdown("#### CupNavi föreslår en lösning")
    st.caption(
        "Förslagen är rangordnade efter minsta praktiska förändring som bedöms ge störst effekt. "
        "Varje knapp genomför ändringen och provar schemat igen direkt. Om det fortfarande inte går ihop visas nästa bästa åtgärd automatiskt."
    )
    if context.get("physical_shortfall", 0) > 0:
        st.error(
            f"Cupen saknar minst {context.get('physical_shortfall', 0)} teoretiska matchplatser med nuvarande plan- och öppettider "
            f"({context.get('capacity', 0)} platser för {context.get('total_matches', 0)} matcher)."
        )

    solutions = []
    if context.get("last_date"):
        minutes = int(context.get("extension_minutes", 30))
        solutions.append({
            "kind": "extend", "title": f"Förläng sista dagens plantider med {minutes} min",
            "effect": f"Skapar ungefär den extra tidskapacitet som behövs för de {unresolved} matcher som saknar tid.",
            "change": f"Endast sluttiden på sista cupdagen ändras (+{minutes} min per tillgänglig plan).",
            "certainty": "Hög" if context.get("physical_shortfall", 0) > 0 else "Medel–hög",
            "score": 10 if context.get("physical_shortfall", 0) > 0 else 30, "minutes": minutes,
        })
    if context.get("late_first"):
        solutions.append({
            "kind": "late_first", "title": "Släpp önskemål om senare första match",
            "effect": f"Frigör tidiga matchtider för {context['late_first']} lag som idag har en hård startbegränsning.",
            "change": "Plantider och matchregler ändras inte; endast lagens reseönskemål tas bort.",
            "certainty": "Medel–hög", "score": 20 if not context.get("physical_shortfall", 0) else 45,
        })
    if context.get("avoid_consecutive") and context.get("consecutive_break", 0) > 0:
        solutions.append({
            "kind": "break", "title": f"Minska extra lagvila ({context['consecutive_break']} min → 0 min)",
            "effect": "Frigör fler möjliga starttider mellan ett lags matcher.",
            "change": "Sportslig återhämtning påverkas, därför rankas detta efter mindre ingripande lösningar.",
            "certainty": "Medel", "score": 40,
        })
    solutions.append({
        "kind": "pitch", "title": "Lägg till en extra plan/spelyta",
        "effect": "Ger en stor och robust kapacitetsökning under samtliga öppettider.",
        "change": "Kräver att arrangören faktiskt har ytterligare en spelplan tillgänglig.",
        "certainty": "Mycket hög", "score": 90,
    })
    solutions.sort(key=lambda item: item["score"])

    for rank, solution in enumerate(solutions, 1):
        with st.container(border=True):
            st.markdown(f"**{rank}. {solution['title']}**")
            main, effect = st.columns([3, 1])
            main.caption(solution["effect"] + " " + solution["change"])
            effect.markdown(f"**Bedömd effekt:** {solution['certainty']}")
            primary = "primary" if rank == 1 else "secondary"
            kind = solution["kind"]
            if kind == "extend":
                minutes = solution["minutes"]
                if st.button(f"Tillämpa +{minutes} min och generera om", key=f"recover_extend_{tournament_id}_{rank}", use_container_width=True, type=primary):
                    deps.apply_extend(tournament_id, tournament, rules, context, minutes)
            elif kind == "late_first":
                if st.button("Ta bort reservationerna och generera om", key=f"recover_late_{tournament_id}_{rank}", use_container_width=True, type=primary):
                    deps.apply_late_first(tournament_id, tournament, rules, context)
            elif kind == "break":
                if st.button("Sätt extrapusen till 0 min och generera om", key=f"recover_break_{tournament_id}_{rank}", use_container_width=True, type=primary):
                    deps.apply_break(tournament_id, tournament, rules, context)
            elif kind == "pitch":
                if st.button("Lägg till 1 plan och generera om", key=f"recover_pitch_{tournament_id}_{rank}", use_container_width=True, type=primary):
                    deps.apply_pitch(tournament_id, tournament, rules, context)

    if context.get("avoid_late"):
        st.caption(
            f"Obs: {context['avoid_late']} lag har önskemål om att undvika den senaste gruppspelsmatchen. "
            "Detta är en mjuk prioritering och blockerar inte i sig schemaläggningen, därför visas den inte som en huvudlösning."
        )
