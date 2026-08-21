# CupNavi 2026.08.21-76-FEATUREPACK

Ny funktionalitet:
1. QR-kod till direktlänkad cupsida (`?cup=<id>`), inklusive nedladdningsbar PNG.
2. Sponsorhantering med nivå, beskrivning, webbplats, logotyp, visningsordning och publik Partners-flik.
3. Funktionärer med roll, plan, kontaktuppgifter, anteckning och styrning av publik kontakt.
4. Drag-and-drop efter automatisk schemaläggning. Matcher dras mellan befintliga tid/plan-slots, ändrade matcher låses och schemat valideras direkt.
5. CSV/XLSX-import med förhandsgranskning för lag och trupper.
6. Publik Matchcenter-sida med matchinformation, resultat, domare och registrerade mål/assist/kort per lag.

Tekniskt:
- Databasschema v3 med sponsors/functionaries och index.
- Backup och health-check omfattar nya tabeller.
- qrcode[pil] och openpyxl tillagda som runtime-beroenden.
