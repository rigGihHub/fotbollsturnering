# CupNavi 2026.09.04-452-GO-LIVE-SCORE-INTEGRITY

Go-live-härdning av resultat och matchhändelser.

- Stoppar resultat som är lägre än redan registrerade målskyttsmål.
- Stoppar rensning av resultat medan registrerade målskyttsmål finns kvar.
- Tillåter fortfarande lagmål utan kopplad spelare, exempelvis självmål eller okänd målskytt.
- Skyddet gäller matchrapportörens snabbsparning, bulkresultat och adminens resultatredigering.
- Behåller specifik integritetsvarning i rapportörsflödet i stället för att felaktigt visa samtidighetsfel.
- Lägger till automatiserad smoke-testsekvens för mål → kvittering → ångra → slutresultat.
- Lägger till GO_LIVE_SMOKE_TEST_V452.md för verkligt tvåmobilers-genrep efter deploy.
- Ingen schemaändring; schema v32 gäller fortsatt.
