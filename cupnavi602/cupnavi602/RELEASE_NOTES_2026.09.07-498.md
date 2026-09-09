# CupNavi 2026.09.07-498-DOCUMENT-TO-CUP

## Dokument → cup
- Nytt review-first-flöde i **Skapa ny cup**: släpp in PDF, TXT eller bild/skärmdump.
- CupNavi extraherar cupnamn, spelort, datum när det tydligt framgår, planer/anläggningar, lagnamn och grupper.
- Hittade uppgifter visas för granskning innan något skrivs till cupen.
- Cupnamn, spelort och datum kan förifyllas direkt i skapandet.
- Granskade lag och grupper kan skapas automatiskt tillsammans med cupen.
- Dubblettlag normaliseras bort innan import.
- Matchschema importeras **inte automatiskt** i v498; schema/resultat lämnas orörda tills ett separat granskningssteg byggs.
- PDF skickas som direkt filinput till OpenAI Responses API, så både text och visuellt innehåll i PDF kan analyseras utan ny runtime-PDF-parser.
- Ingen fil skickas till AI om `OPENAI_API_KEY` saknas.

## Säkerhet och prestanda
- Lag/grupp-import sker atomiskt i en separat transaktion.
- Inga ändringar i resultat-, matchrapportörs- eller slutspelssäkerhet.
- `app.py` ligger fortsatt under projektets performance-contract för storlek.
