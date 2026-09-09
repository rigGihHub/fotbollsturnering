# CupNavi v444 – Public first-paint fast path

Fokus: kortare faktisk väntetid på den publika Matcher-vyn.

- Målskyttar och kort laddas inte längre från databasen på första renderingen. Besökaren väljer **Visa målskyttar och kort** när detaljerna behövs. Exakt matchlänk laddar dem automatiskt.
- Matchkort, resultat, tider och planer visas fortfarande direkt.
- Toppskytten hämtas nu via en ren scorer-query. Den tidigare kombinerade overview-frågan räknade också aktiva besökare trots att den siffran inte längre visas på Matcher.
- Toppskyttens korta live-cache behålls på 15 sekunder.
- Ingen tävlings-, poäng- eller schemalogik ändrad.
