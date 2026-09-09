# v423 — Public Info cold start

- Info är publik standardflik och laddar inte längre hela matchschemat eller alla lag före första renderingen.
- En liten SQL-aggregatfråga avgör om cupen är färdig och om cupsummering kan erbjudas.
- Hela matchlistan hämtas först om besökaren faktiskt öppnar den valfria cupsummeringen.
- Övriga publika flikar behåller befintlig funktionalitet och datavägar.
- Målet är färre och mindre Turso-läsningar på den vanligaste första sidladdningen, särskilt för stora cuper.
