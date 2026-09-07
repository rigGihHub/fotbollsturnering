# CupNavi v483 — Recovery UX

Efter ett osäkert skrivfel får rapportören nu en konkret återhämtningsväg i stället för att behöva gissa.

- **Läs om från servern** rensar render-cache och hämtar nytt serverläge.
- CupNavi gör ingen automatisk omskrivning.
- För snabbresultat sparas det försökta resultatet i sessionskontexten.
- Efter omläsning kan CupNavi säga om exakt samma resultat redan finns på servern.
- Om resultatet redan finns visas tydligt att det inte ska registreras igen.
- För andra åtgärder visas färskt serverläge och rapportören måste kontrollera innan ny ändring.
- Återhämtningsläget avslutas först när användaren bekräftar att serverläget har kontrollerats.

Ingen schemaändring. Schema v32.
