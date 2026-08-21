# CupNavi 2026.08.21-85-IMPORT-WIZARD

Importen är ombyggd till ett femstegsflöde:
1. Välj Lag eller Trupper.
2. Ladda upp CSV/XLSX.
3. Automatisk kolumnigenkänning + manuell kolumnmappning.
4. Validering, sammanfattning, förhandsgranskning och nedladdningsbar felrapport.
5. Aktiv bekräftelse innan import.

Robusthet:
- CSV-avgränsare autodetekteras (komma, semikolon, tab m.m.).
- Flera vanliga textkodningar provas.
- Excel-filer kan ha flera blad och användaren väljer blad.
- Svenska och engelska kolumnrubriker känns igen.
- Dubbletter upptäcks före import.
- Färger, tider, resväg, tröjnummer och födelseår valideras.
- Okända lag i truppimport blockeras tydligt.
- Maxantal lag kontrolleras före och inne i transaktionen.
- Importskrivningen sker transaktionellt; vid fel rullas hela importen tillbaka.
- Lagimport markerar schemat som ändrat och avpublicerar för att undvika ett inaktuellt publikt schema.
