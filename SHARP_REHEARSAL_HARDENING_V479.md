# CupNavi v479 — Sharp Rehearsal Hardening

## Bakgrund
v455 skapade den första obligatoriska skarpa genrepsporten.
v475–v478 har sedan gjort slutspelsresultat betydligt säkrare.

v479 gör dessa skydd till verkliga GO/NO-GO-kontroller.

## Utan slutspel
9 obligatoriska moment kvarstår:
reporter, publik, mål, undo, samtidighetskonflikt, nätverksavbrott,
avslut, persistence och tabell.

## Med slutspel
Fyra ytterligare obligatoriska moment:
1. rätt lag/placering går in i slutspelet,
2. farlig uppströms resultatkorrigering blockeras,
3. kedjan kvartsfinal → semifinal → final skyddas,
4. säker recovery av en oanvänd downstream-match verifieras.

Totalt 13 obligatoriska moment när slutspel används.

## Viktigt
Browser push är fortsatt inte ett startkrav.
Turso-lagring, publik livevy, resultat, tabell och slutspelskedjan är startkrav.
Ingen schemaändring. Schema v32.
