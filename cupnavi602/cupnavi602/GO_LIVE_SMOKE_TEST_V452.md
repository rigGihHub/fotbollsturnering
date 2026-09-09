# CupNavi v452 – Go-live smoke-test

Det här testet ska köras efter deploy av v452 och före första riktiga cupen.

## Kritisk matchkedja

1. Starta en testmatch från två mobiler: rapportör + publik.
2. Registrera 1–0 med målskytt. Kontrollera resultat och målskytt publikt.
3. Registrera 1–1 med målskytt. Kontrollera tabell/livevy.
4. Ångra senaste målet. Kontrollera att både resultat och målskytt går tillbaka.
5. Försök manuellt sätta resultatet lägre än antalet registrerade målskyttsmål. CupNavi ska stoppa sparningen.
6. Korrigera målskytt först och spara därefter det lägre resultatet. Det ska fungera.
7. Kör två rapportörer samtidigt mot samma match. En stale ändring ska nekas, inte skriva över.
8. Bryt nätet på rapportörsmobilen, återanslut och ladda om. Senaste Turso-data ska visas utan dubbletter.
9. Sätt matchen till slut och kontrollera resultat, tabell, skytteliga och eventuell slutspelsavancemang.
10. Stäng båda webbläsarna, öppna på nytt och verifiera att allt finns kvar.

## Godkänt

Skarpt läge godkänns först när samtliga steg ovan fungerar i den deployade Streamlit + Turso-miljön.
