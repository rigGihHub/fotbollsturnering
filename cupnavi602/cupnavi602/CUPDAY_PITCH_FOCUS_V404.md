# CupNavi v404 — Cupday pitch focus

Cupdagen visar nu en kompakt **Planer just nu**-översikt direkt i huvudflödet. Den återanvänder redan byggd snapshot-data och gör inga nya databasfrågor. Upp till sex planer visas med aktuell eller nästa match och status; fler planer finns kvar i den befintliga Planstatus-detaljen.

Livekortets väg till rapportering heter nu **Rapportera resultat / händelser**. Dessutom har `build_cup_day_snapshot()` fått `require_results`: när en turnering räknar resultat räknas en match som markerats slut men fortfarande saknar score inte som färdig, utan ligger kvar som åtgärd. Resultatfria matchcamps kan fortfarande avslutas utan score.

Mobilvyn använder två plankort per rad och går över till en kolumn på mycket smala skärmar.
