# CupNavi 2026.09.08-533 – Cup-day server window

Prestandafokus: den vanliga publika Matcher-vyn behöver inte längre hämta hela matchprogrammet under själva cupdagen.

- Första matchlistan hämtas server-side i samma 12-matchersbatch som den faktiskt visar.
- En separat liten tidslucka runt aktuell tid hämtas i samma SQL-roundtrip för Pågår nu / Nästa matcher.
- Totalt antal matcher, spelade matcher och mål räknas exakt i databasen i samma anrop, så sammanfattningen blir korrekt trots den mindre batchen.
- Explicit lagfilter, planfilter, matchlänk, sökning, highlights och Spelade/Kommande behåller full-data-vägen för korrekt beteende.
- Framtida cupers v532-fast path är kvar oförändrad.
