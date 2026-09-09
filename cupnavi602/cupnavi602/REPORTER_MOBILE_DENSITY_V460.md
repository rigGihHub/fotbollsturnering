# CupNavi v460 — Reporter Mobile Density

## Fokus
Göra Matchrapportörens vanligaste mobilflöde tätare utan att röra resultatsäkerheten.

## Förändrat
- Snabbresultatet ligger i en egen mobil-shell.
- På skärmar under 390 px får just denna panel behålla horisontell layout i stället för att globalt staplas.
- Hemma/borta −/+ ligger kvar bredvid varandra.
- Resultatet ligger stort i mitten.
- `Spara resultat` får större bredd än återställning.
- `Återställ` visas som en kompakt ↺-knapp med hjälptext.
- Matchköns text kortas till `X kvar · Y klara`.
- Enkel-lägets hjälprad kortas.

## Säkerhet
- Samma callback för +/−.
- Samma callback för spara resultat.
- Samma callback för återställ.
- Ingen writer, optimistic lock, DB-fråga eller resultatvalidering ändras.
- Schema v32.
