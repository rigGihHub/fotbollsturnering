# CupNavi v466 — Multi Favorites + Public PDF

## Flera favoritlag
- Publiken kan följa flera lag samtidigt.
- Favoriter kan ligga i olika ålders-/tävlingsklasser.
- Klass visas i lagvalet när `age_class` finns.
- Favoriter sparas i `teams=` i den publika URL:en.
- Första favoriten är aktiv detaljvy; övriga visas i en kompakt överblick och kan öppnas direkt.
- All favoritöversikt återanvänder redan laddade publika matcher.

## PDF i turneringsvyn
- Ny publik `Skriv ut / PDF`-yta direkt i Turneringsvy.
- PDF skapas först efter aktivt knapptryck.
- Samma `build_cup_program_pdf` används som i admin.
- Endast publicerade, schemalagda matcher tas med.
- Den skapade PDF:en kan laddas ner och därefter skrivas ut från mobil eller dator.

## Säkerhet/prestanda
Ingen schemaändring. Ingen PDF-DB-kostnad på normal publik first paint.
Schema v32.
