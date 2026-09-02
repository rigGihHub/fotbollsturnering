# CupNavi – prioriterad produktgranskning v364

## 10 viktigaste förbättringarna

1. **Gör Matchcamp och Turnering till explicita produktlägen**
   Nuvarande implementation saknade egen arrangemangstyp och använde i praktiken resultaträkning som proxy. Det gör att matchcamp-flödet riskerar att exponera turneringslogik. Hög UX-nytta, låg risk om befintliga arrangemang defaultar till Turnering.

2. **Samla publiceringskontrollen till en enda sanningskälla**
   Validering, readiness, schemavarningar och publiceringsstatus finns redan men är fördelade över flera ytor. En enda modell för Kritiska fel / Varningar / Förbättringar minskar risken för felpublicering.

3. **Gör “Optimera schema” till en riktig åtgärd**
   CupNavi kan analysera schemakvalitet, men det saknas en tydlig generell loop där identifierade problem kan förbättras automatiskt och jämföras före/efter.

4. **Ge Matchcamp en egen schemamålsmodell**
   Matchcamp behöver prioritera jämnt antal matcher, jämn speltid, vila och bra motstånd snarare än grupp-/slutspelslogik.

5. **Gör Mitt lag till publikens primära mobilväg**
   Favoritlagsfunktioner finns, men upplevelsen bör ännu tydligare starta i nästa match, plan, motståndare och ändringar utan att användaren söker i hela cupen.

6. **Förbättra live-status från uppskattning till verkligt läge**
   Cupdagen uppskattar pågående/försenade matcher från schematid och matchlängd. Ett explicit start-/slut-/förseningsläge skulle ge säkrare driftinformation.

7. **Förenkla resultatrapportering till två tydliga nivåer**
   Enkel rapportering ska vara extremt snabb, medan mål/assist/kort endast visas när avancerad rapportering är aktiverad.

8. **Slutför tröjmodellen och färgkrockshanteringen**
   Hemma-/bortafärg och mönster finns, men shorts/strumpor och en tydligare automatisk rekommendation om reservställ saknas.

9. **Gör återanvändning av tidigare arrangemang mer selektiv**
   Kloningsstöd finns, men användaren bör kunna välja exakt vilka delar som återanvänds: planer, tider, regler, lag, grupper och slutspelsstruktur.

10. **Fortsätt server-side behörighetsgranskningen**
    Roller finns, men varje skrivväg bör systematiskt verifieras mot server-/backendbehörighet och inte bara UI-synlighet inför större skalning.

## Genomfört i v364

- Ny datamodell: `arrangement_type` med `tournament` / `matchcamp`.
- Migration v28 är bakåtkompatibel: befintliga arrangemang blir Turnering och ändrar inte beteende.
- Setup frågar tidigt “Vad arrangerar ni?” innan klass-, plan- och formatval.
- Matchcamp får eget förklarande språk och resultat är avstängt som standard när användaren väljer Matchcamp.
- Matchcamp kan fortfarande aktivera resultatrapportering utan att CupNavi samtidigt aktiverar slutspel.
- Byte tillbaka till Turnering aktiverar inte resultat eller andra tävlingsval tyst.
- Matchcamp hålls explicit fri från automatisk slutspelslogik i setup-flödet.
