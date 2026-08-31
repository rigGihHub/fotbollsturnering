# CupNavi v343 – Create Cup Visual Refresh

Version: `2026.08.31-343-CREATE-CUP-VISUAL-REFRESH`

## Förändringar
- Skapa ny cup får en tydlig produktlik startyta med stegvis struktur: Grund → Tävlingsklasser → Kapacitet → Regler.
- Huvudytan använder tvåkolumnslayout på större skärm och responsiv två-raders stegvisning på mobil.
- Startmall tonas ned till ett valfritt avancerat val.
- Testmiljö är standard för alla nyregistrerade cuper i skapaflödet.
- Duplicerad ny upplaga förväljer också Testkopia.
- Tydlig grön statusyta visar att den nya cupen skapas som testmiljö.
- Språkfelet `Efter Skapa guidar ...` ersätts med `När cupen är skapad guidar CupNavi dig vidare ...`.
- Befintlig create/write-path, setup-wizard, sportprofil, locale/tidszon/land och schema-defaults behålls.

## Dataintegritet
Ingen databasmigrering. Miljötypen sparas fortsatt i befintligt `environment_type`. Produktion kan fortfarande väljas aktivt under Fler alternativ.
