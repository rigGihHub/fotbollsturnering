# CupNavi v1.250 – Matchrapportörskod

## Nytt flöde
- Admin skapar en **fyr­siffrig numerisk kod** under **Domare → Matchrapportörskod**.
- Matchrapportören väljer turnering och anger koden vid inloggning.
- Koden är turneringsspecifik: en kod ger bara åtkomst till den aktuella turneringen.
- Ny kod kan genereras när som helst. Den gamla koden slutar då gälla direkt.
- Aktiva matchrapportörssessioner som bygger på den gamla koden loggas också ut när koden roteras.

## Säkerhet
- Koden sparas inte i klartext i databasen.
- CupNavi använder saltad PBKDF2-hash via samma verifieringsprincip som lagportalens åtkomstkoder.
- Själva fyrsiffriga koden visas endast direkt efter generering så att admin kan kopiera/dela den.
- Inloggningen har fortsatt server-side rate limiting, nu per turnering.
- Befintliga Streamlit Secrets för matchrapportör behålls som bakåtkompatibel fallback.

## UX
Koden är medvetet kort eftersom rollen används under cupdag och ofta från mobil. Rate limiting,
turneringsscope och kodrotation begränsar risken som följer med en kort kod.
