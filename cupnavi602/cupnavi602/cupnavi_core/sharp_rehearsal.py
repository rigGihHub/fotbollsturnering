"""Pure sharp-rehearsal rules used before CupNavi is approved for a real cup."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class RehearsalStep:
    key: str
    label: str
    required: bool = True


@dataclass(frozen=True)
class SharpRehearsalVerdict:
    steps: tuple[RehearsalStep, ...]
    completed_required: int
    required_count: int
    technical_ready: bool

    @property
    def rehearsal_complete(self) -> bool:
        return self.completed_required == self.required_count

    @property
    def approved(self) -> bool:
        return self.technical_ready and self.rehearsal_complete

    @property
    def remaining(self) -> tuple[RehearsalStep, ...]:
        return tuple(step for step in self.steps if step.required and not getattr(self, "_done", {}).get(step.key, False))


def rehearsal_steps(*, has_playoff: bool) -> tuple[RehearsalStep, ...]:
    steps = [
        RehearsalStep("reporter", "Mobil A: logga in som matchrapportör och öppna testmatchen"),
        RehearsalStep("public", "Mobil B: öppna samma match i den publika cupvyn"),
        RehearsalStep("goal", "Registrera 1–0 med målskytt och kontrollera publikmobilen"),
        RehearsalStep("undo", "Ångra målet och kontrollera att både resultat och målskytt återställs"),
        RehearsalStep("conflict", "Gör samtidiga ändringar från två rapportörssessioner och verifiera konfliktskyddet"),
        RehearsalStep("network", "Bryt nätet kort, återanslut och verifiera att inget dubbelregistreras"),
        RehearsalStep("finish", "Slutför testmatchen och verifiera slutresultatet efter omladdning"),
        RehearsalStep("persistence", "Öppna cupen i en ny session/enhet och verifiera att resultat och händelser finns kvar"),
        RehearsalStep("table", "Verifiera att tabellen/statistiken räknas om från det färdiga resultatet"),
    ]
    if has_playoff:
        steps.extend([
            RehearsalStep(
                "playoff",
                "Verifiera att färdiga gruppresultat ger rätt lag/placering i slutspelet",
            ),
            RehearsalStep(
                "playoff_dependency",
                "Ändra ett tidigare slutspelsresultat och verifiera att CupNavi blockerar ändringen om en beroende senare match redan används",
            ),
            RehearsalStep(
                "playoff_chain",
                "Verifiera en kedja över flera slutspelsled, till exempel kvartsfinal → semifinal → final, så att indirekta beroenden också skyddas",
            ),
            RehearsalStep(
                "playoff_recovery",
                "På en oanvänd beroende slutspelsmatch: verifiera att säker återställning fungerar och att korrigeringen därefter kan göras utan att schema eller matchkällor förstörs",
            ),
        ])
    return tuple(steps)


def build_sharp_rehearsal_verdict(
    *,
    technical_ready: bool,
    completed: Mapping[str, bool],
    has_playoff: bool,
) -> SharpRehearsalVerdict:
    steps = rehearsal_steps(has_playoff=has_playoff)
    required = tuple(step for step in steps if step.required)
    completed_required = sum(1 for step in required if bool(completed.get(step.key, False)))
    verdict = SharpRehearsalVerdict(
        steps=steps,
        completed_required=completed_required,
        required_count=len(required),
        technical_ready=bool(technical_ready),
    )
    # Keep the public dataclass small while still making remaining steps available.
    object.__setattr__(verdict, "_done", {step.key: bool(completed.get(step.key, False)) for step in steps})
    return verdict
