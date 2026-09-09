# v340 – Initial Setup Simplification

Version: `2026.08.31-340-INITIAL-SETUP-SIMPLIFICATION`

## Syfte
Göra första cupkonfigurationen kortare utan att ta bort avancerad kontroll.

## Förändringar
- Standardflödet är nu **Grund → Kapacitet → Lägg till lag**.
- Den gamla sjustegsindikatorn har ersatts av ett trestegsflöde som speglar vad som faktiskt krävs för snabbstart.
- Snabbstart är fortsatt primär CTA när tävlingsklass, planerat lagantal och giltiga plantider finns.
- Formatförslag, poäng, matchregler, schemaprioriteringar, lagönskemål, service, kontrolltabell och publik statistik ligger nu bakom **Visa avancerade inställningar**.
- Avancerade write-paths och autosparande är oförändrade; de renderas bara på begäran.
- Ingen databasstruktur, publiceringslogik, schemagenerering eller concurrency har ändrats.

## Produktprincip
En ny arrangör ska inte behöva fatta beslut som CupNavi redan har rimliga standardvärden för innan lag kan registreras.
