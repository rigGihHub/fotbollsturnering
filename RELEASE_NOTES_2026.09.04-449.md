# CupNavi 2026.09.04-449 – Mobile Playoff Action

- Gör varje publikt slutspelskort på mobil handlingsbart med direktlänk till exakt match.
- Live- och pausmatcher får den tydligare CTA:n **Följ matchen nu**; övriga matcher visar **Öppna match**.
- Behåller valt favoritlag/Min cup via `team`-parametern när användaren går från slutspelet till matchen.
- Återanvänder befintlig direct-match-routing och redan laddad slutspelsdata: inga nya DB-anrop och ingen extra `st.rerun()` i renderingen.
