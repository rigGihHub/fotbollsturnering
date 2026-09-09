# CupNavi v589 – UX-granskning av Steg 2 · Lag

## Mål
Lag-steget ska ha en enda huvuduppgift: få in de lag som deltar och därefter gå vidare till Grupper.

## Problem som fanns
- Tröj setup låg som en fullbreddsknapp före själva sidrubriken och konkurrerade med huvuduppgiften.
- AI-import av spelare låg öppet i huvudflödet trots att spelartrupper inte krävs för att skapa cupens struktur.
- Standardtabellen över lag visade kontakt- och reseuppgifter som inte behövs för nästa setupbeslut.
- Sidan innehöll många bra funktioner, men informationshierarkin gjorde dem lika visuellt viktiga som själva lagregistreringen.

## Förändringar i v589
- Tröj setup flyttad till Fler lagverktyg.
- Spelare från bild är nu en stängd, valfri sektion.
- Nytt lag-formuläret fortsätter att visa bara det som krävs först; tröjor/kontakt/resor ligger under Valfritt.
- Standardlistan över registrerade lag visar endast Lag, Tävlingsklass och Grupp.
- Kontakt- och resedetaljer visas endast när användaren öppnar dem.
- När planerat antal lag är registrerat är den primära handlingen Fortsätt till Grupper.

## UX-bedömning efter ändringen
Den normala resan är nu: status → lägg till nästa lag → upprepa → fortsätt till Grupper. Det är betydligt närmare en linjär wizard och minskar risken att en ovan arrangör börjar konfigurera sekundära funktioner för tidigt.

## Nästa förbättring
Steg 3 · Grupper bör få samma behandling: en tydlig huvudfråga (hur ska lagen delas in?), ett rekommenderat förstaval, import/foto och manuell detaljhantering som sekundära vägar, samt en enda tydlig CTA mot Regler när gruppindelningen är klar.
