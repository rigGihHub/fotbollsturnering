# CupNavi v530 – Public Core Fused Read

Prestandafokus: den publika Matcher-vyn hämtade publicerade matcher och lag i två separata SQL-anrop mot samma Turso-anslutning. När båda projektionerna behövs på första paint slås de nu ihop till ett enda `UNION ALL`-anrop och delas upp lokalt efter hämtning.

Detta tar bort en blockerande remote roundtrip utan att minska datamängden, ändra filtrering eller ta bort funktionalitet. Rutter som bara behöver matcher eller bara lag behåller sina smalare separata queries.

Verifiering i denna nattliga prestandaiteration: fokuserade v530-tester gröna, `compileall` grön och den sammanslagna queryn verifierad mot SQLite med både match- och lagrader. Full release-regression skjuts till det samlade push-klara paketet.
