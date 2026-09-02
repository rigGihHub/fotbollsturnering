# v375 – Autopilot jämför återhämtningsalternativ

- CupNavi Autopilot jämför nu flera sätt att hantera en konstaterad planförsening.
- Alternativen vägs mot antal ändrade matcher, antal berörda lag, total tidsförskjutning, regelkonflikter och kvarvarande försening.
- Nytt alternativ: låt befintliga luckor absorbera förseningen, så färre matcher flyttas när schemat har marginal.
- Nytt alternativ: flytta bara nästa match till en annan ledig plan när det räcker för att den försenade planen ska komma ikapp.
- Befintligt alternativ att skjuta alla senare matcher lika mycket finns kvar som konservativ standard.
- Gör ingenting visas som jämförelsebas men rekommenderas inte när en känd försening lämnas olöst.
- Cupdagen visar Autopilots rekommendation direkt.
- Knappen Jämför lösningar öppnar Cupverktyg med plan och försening förifyllda.
- Varje alternativ visar exakt vilka matcher, tider och planer som skulle ändras.
- Jämförelsen är helt preview-first; inga schemaändringar görs automatiskt.
- Ingen schemaändring; databasschema kvar på v30.
