# CupNavi v322 – Public fragment + cold-start fast path

## Problem
Publika widgetklick körde om hela Streamlit-skriptet. Dessutom spelade varje ny app-process upp den stora idempotenta schema-bootstrapen mot Turso även när databasen redan låg på senaste schema.

## Ändring
- Hela `render_public_view` är nu ett Streamlit-fragment. Publika navigationer, filter, favoritlag och övriga widgetklick stannar i fragmentet i stället för att köra om hela `app.py`.
- Tidigare underfragment för Statistik, Cupinfo och Matcher har tagits bort för att undvika fragment-i-fragment.
- Publika explicita reruns använder `scope="fragment"`.
- Favoritlagets knapp "Visa mitt lags matcher" använder aktuell v167-state och kanonisk `section=matches`.
- `init_db()` har en read-only schemafingerprint. Om migrationsversion och kritiska tabeller/kolumner är kompletta hoppar en kall process över den stora DDL-bootstrapen. Vid minsta avvikelse används exakt den befintliga fulla repair/migrationsvägen.

## Säkerhet
Ingen migrationslogik tas bort. Fast path är endast tillåten när senaste schema-markeraren och kritiska schemaobjekt kan läsas. Saknad tabell/kolumn eller gammal version ger omedelbar fallback.
