# CupNavi v453 – nätgenrep

Kör detta efter deploy, med två telefoner och en testmatch.

1. Telefon A öppnar Matchrapportör. Telefon B öppnar publik matchvy.
2. A registrerar 1–0 och väntar på grön text **Mål säkert sparat på servern**.
3. Tryck snabbt två gånger på nästa mål under normal uppkoppling. Kontrollera att endast en serverändring sker per lyckat stale-säkert flöde och att resultat + målskytt aldrig divergerar.
4. Slå på flygplansläge på A. Öppna **Offlineutkast** och kontrollera att status visar Offline. Ändra resultatet och kontrollera att det autosparas lokalt.
5. Återställ nätet. Kontrollera att status visar Online. Kopiera utkastet och för över det manuellt till riktig rapportering. Offlineutkastet får aldrig beskrivas som automatiskt synkat.
6. Simulera osäker återkoppling: registrera mål, avbryt nätet direkt efter trycket, återanslut och ladda om. Kontrollera serverns aktuella resultat innan du trycker igen.
7. På B: kontrollera resultat, målskytt, tabell/statistik och omladdning.

Godkänt först när resultat och spelarhändelser är identiska efter omladdning på båda enheterna.
