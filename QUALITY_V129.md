# CupNavi 2026.08.24-129-TOURNAMENT-SETUP-RANKING

## Ändringar
- Turneringsvyn visar rubriken **Matcher spelade** med värdet `x av y`.
- Testverktyget låter Admin välja antal testlag och 2/4/8 testgrupper innan testdata skapas.
- Testnivå (halvt gruppspel → färdig cup) är låst tills testdata faktiskt har skapats.
- Valbar slutlig 1–N-ranking av alla lag, vald redan när turneringen skapas.
- Lag kan önska att undvika dagens senaste gruppspelsmatch; schemaläggaren behandlar det som ett mjukt önskemål.
- Efter att en ny turnering skapats öppnas en separat obligatorisk konfigurationssida för tävlingsstruktur, regler, schema, slutspel och statistik.
- Databasschema v15.

## QA
- Python syntax/compileall: OK
- Full pytest: 303 tester passerade
- Ny regressionstäckning för v129-flöden och schemafält
