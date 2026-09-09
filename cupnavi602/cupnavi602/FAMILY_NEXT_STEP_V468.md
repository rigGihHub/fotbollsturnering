# CupNavi v468 — Nästa för familjen

## Nytt
- När flera favoritlag följs visas ett tydligt kort `Nästa för familjen`.
- Kortet visar hur många minuter det är till nästa favoritmatch.
- Nästa match, favoritlag och plan visas direkt.
- Om ytterligare en favoritmatch finns visas hur många minuter senare den startar.
- Om planen ändras visas `byt plan X → Y`.
- Om nästa favoritmatch ligger inom 60 minuter markeras övergången med `⚠`.
- Samma plan markeras uttryckligen när planbyte inte behövs.

## Avgränsning
CupNavi säger inte att tiden räcker för att gå eller köra mellan planerna om faktisk restid saknas. Vyn visar endast schemagap och planbyte.

## Prestanda
Bygger helt på den redan skapade favorit-tidslinjen och laddade publika matcher.
Ingen ny DB-fråga eller rerun.

## Säkerhet
Ingen schema-, resultat-, auth- eller writerlogik ändras.
Schema v32.
