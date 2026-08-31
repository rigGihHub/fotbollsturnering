# CupNavi v354 – Address readiness fix

- Fixar ett grundfel där verifieringsbocken för planadress sparades men inte lästes tillbaka i planmetadata.
- `pitch_definitions()` hämtar nu `address_verified` och reparerar v26-kompatibilitet vid blandade molnscheman.
- Setupens readiness använder checkboxens faktiska tillstånd i samma render, så en ibockad adress räcker direkt.
- Ändrad adress återställer fortfarande verifieringen automatiskt.
- Varningen om overifierade adresser och knappen `Fortsätt → Lägg till lag` använder samma källa till sanning.
