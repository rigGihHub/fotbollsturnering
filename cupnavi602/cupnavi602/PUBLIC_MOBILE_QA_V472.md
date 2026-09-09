# CupNavi v472 — Public Mobile QA

## Mina lag
- Primär nästa-match-knapp ligger kvar direkt synlig.
- Målskyttar/kort för senaste resultat ligger under `Mer om senaste resultatet`.
- Väder och vägbeskrivning ligger under `Väder & vägbeskrivning`.
- Vägbeskrivning är fortsatt lazy; DB-frågan körs endast efter uttryckligt val.
- Väder är fortsatt lazy och aktiveras först efter knapptryck.

## Matcher
- Målskyttsreglaget visas inte när inga synliga matcher är spelade.
- Exakt match använder en kompakt caption i stället för stor informationsruta.
- Direkt vädergenväg visas bara för matcher inom 120 minuter.

## Effekt
Mindre vertikal trängsel och färre sekundära beslut på mobil utan att funktioner tas bort.

Schema v32.
