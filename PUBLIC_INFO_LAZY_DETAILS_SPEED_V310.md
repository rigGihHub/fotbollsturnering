# v1.310 – Public Cupinfo lazy details speed

## Mål
Förenkla Cupinfo och undvika read-only DB-anrop för sekundärt innehåll som användaren inte har bett att se.

## Ändrat
- Ny opt-in `Visa fler cupdetaljer`.
- Lagkontakter, funktionärer, erbjudanden och partners laddas först när opt-in aktiveras.
- Tidigare låg innehållet i kollapsade expanders, men deras DB-frågor kördes ändå vid varje Cupinfo-render.
- Standardflödet kan därmed undvika upp till fyra sekundära DB-frågor.
- Feedbackformuläret påverkas inte.

## Risk
Låg. Inga write paths, auth-, schema-, publicerings-, resultat- eller concurrency/CAS-flöden är ändrade.
