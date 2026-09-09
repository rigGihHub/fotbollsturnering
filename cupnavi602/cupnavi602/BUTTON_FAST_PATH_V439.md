# CupNavi v439 — Button Fast Path

Version: `2026.09.04-440-PUBLIC-BUTTON-FAST-PATH`

## Varför
På cupdagen är Matchrapportör den mest klickintensiva ytan i CupNavi. Flera av de vanligaste knapparna gjorde tidigare först Streamlits normala widget-rerun och därefter ett explicit `st.rerun()`. Det gav två appkörningar för ett enda knapptryck.

## Förändrat
- `+` / `−` för snabbresultat använder nu `on_click`-callbacks som uppdaterar score draft **innan** Streamlits normala rerun.
- `Återställ` använder samma single-rerun-princip.
- `Spara resultat` skriver till databasen i callbacken före den normala rerunnen, så den efterföljande renderingen läser det färska resultatet direkt utan extra rerun.
- Matchstatus (`Ej startad`, `Pågår`, `Paus`, `Slut`) använder samma callbackmönster.
- Föregående/nästa spelare i livehändelser använder callback i stället för ett extra explicit `st.rerun()`.
- Konflikter vid samtidig rapportering visas som en beständig flash-varning efter rerunnen.
- Performance Contract bevakar nu att de viktigaste cupdagsknapparna fortsätter använda single-rerun-vägen.

## Effekt
Det minskar antalet fulla Streamlit-körningar för de mest frekventa cupdagsinteraktionerna från två till en. Det ger mindre väntetid efter varje tryck och minskar samtidig belastning på app och databas.

## Avgränsning
Detta är en säker, fokuserad prestandaförbättring. Ingen domänlogik, poängräkning eller schemalogik ändras.
