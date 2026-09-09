# CupNavi v477 — Playoff Correction Recovery

## Syfte
När v475/v476 blockerar en uppströms slutspelskorrigering kan admin nu återställa en beroende downstream-match om den i praktiken ännu inte har spelats.

## Recovery får endast köras när
- matchstatus är `not_started`,
- ingen faktisk starttid finns,
- inga registrerade matchhändelser finns.

Ett felaktigt eller för tidigt inmatat resultat får däremot nollställas.

## Vad återställs
- hemma-/bortamål,
- straffresultat,
- manuellt beslutad vinnare,
- avslutad-status/tid.

## Vad rörs inte
- home_source / away_source,
- speltid,
- plan,
- domare,
- publiceringsstruktur.

Åtgärden loggas i audit trail. Om matchen ändrats på annan enhet blockeras reset.
Ingen schemaändring. Schema v32.
