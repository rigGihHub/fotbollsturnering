# v432 – Premium Cup Program

CupNavi får en ny, deltagarvänlig PDF-produkt: **Cupprogram**.

## Varför
Den tidigare PDF-exporten var ett funktionellt administrativt schemapaket. Den saknade den visuella hierarki och berättande struktur som krävs för ett officiellt program som arrangörer vill dela med lag, publik och sponsorer.

## Nytt
- Ny `build_cup_program_pdf(...)` i `cupnavi_core/pdf_export.py`.
- Porträtt A4 med CupNavi-identitet, hero, cupfakta, planinformation, gruppkort och lagfärger.
- Gruppspel i kompakt programtabell.
- Slutspel med separat visuell hierarki.
- Automatiskt bracket-liknande "Vägen till finalen" när två semifinaler + final finns.
- Utskriftsvänliga tabeller per grupp.
- Automatisk "Att tänka på" från CupNavis faktiska regler (lagvila, resor, skiljeregler, slutspelsregel och arrangörsinformation).
- Planernas namn/adresser används när de finns.
- "Skapa professionellt cupprogram" är primär PDF-åtgärd i Schema.
- Det gamla kompletta detaljschemat finns kvar som sekundär administrativ export.

## Nästa designsteg
Den nya motorn är avsiktligt separerad från den gamla detaljexporten. Nästa steg kan därför lägga till hero-bild, cup-/föreningslogotyp, klubbmärken, sponsorer och fler designmallar utan att påverka schemalogiken.
