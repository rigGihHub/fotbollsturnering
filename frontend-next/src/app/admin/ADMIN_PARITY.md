# CupNavi admin parity — v628

Next-admin är nu strukturellt förberedd för hela CupNavi-flödet. Ingen modul får märkas som fungerande förrän den använder riktig data och kan testas.

## Migreringsordning
1. Cupinfo: autentiserad läsning/skrivning av namn, datum, anläggning och kontakt.
2. Lag: klasser, lag, tröjfärger och laguppställning/import.
3. Grupper: gruppindelning och validering.
4. Planer & tider: anläggningar, planstorlek, tillgänglighet, matchlängd och paus.
5. Regler: poäng, vila, två matcher i rad, färgkrock och dynamiskt schema.
6. Schema: generering, importskydd och manuell redigering.
7. Domare: skapa/tillsätta nu eller senare.
8. Slutspel: A/B, kvalificerade placeringar, brons och final.
9. Publicering: riktig checklista + förhandsgranskning före publicering.
10. Matchrapportering: resultat, mål, assist, gula/röda kort.
11. Import: flera bilder/dokument, tolkningsgranskning och skrivskydd mot befintligt schema.
12. PDF/export: preview, skapa + ladda ned i ett flöde; aldrig tom PDF.

## UX-regler
- Samma cupnamn överallt.
- Rollkoder ska vara nära till hands men aldrig fabriceras.
- Publik vy ska behålla CupNavis egen serietidning + fotbollskort + Text-TV + framtid-identitet.
- Väder, tabeller och målskyttar visas som standard när respektive data/funktion är aktiverad.
- Topplistor visas endast om de aktiverats av admin.
- Mobil admin ska vara ett förstaklassflöde, inte desktop nedtryckt på smal skärm.
