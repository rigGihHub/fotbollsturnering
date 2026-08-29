# CupNavi v1.292 – Mobile table + navigation focus

## Bakgrund
Live-skärmdump från Android visade två tydliga UI-problem i den publika cupvyn:
1. grupptabellen blev för bred och slutspelsetiketterna pressades/överlappade i sista kolumnen,
2. huvudnavigationen Cupinfo / Schema / Tabeller / Slutspel / Statistik smälte ihop med sidans vita bakgrund och behövde tydligare fokus.

## Ändringar
- Publik grupptabell har en mobil layout under 600 px.
- Tabellen använder fast layout på mobil och döljer GM/IM för att prioritera Lag, matcher, utfall, målskillnad, poäng och vidare-status.
- Lagkolumnen får större andel av bredden och ellipsis vid extrema lagnamn.
- Sista kolumnen heter `Vidare` på mobil och visar kompakta kvalificeringsmarkörer (`1:a`, `2:a`, `A`, `B` eller `✓`) i stället för långa texter som kan överlappa.
- Desktop behåller full statistik och full slutspelsetikett.
- Publik huvudnavigation har nu en sammanhängande CupNavi-grön bakgrund över hela knappraden.
- Inaktiva val visas vitt på grönt; aktiv sida visas som vit markerad knapp med grön text.

## Scope
Endast presentation/CSS/HTML för publik tabell och publik navigation. Ingen DB-, schema-, resultat-, publicerings-, auth- eller concurrencylogik ändrad.
