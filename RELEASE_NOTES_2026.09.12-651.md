# CupNavi v651 — aktiv cupkontext

- Återställer senast valda behöriga cup efter omladdning och ny inloggning.
- Stödjer direkta adminlänkar med `?cup=<id>`.
- Validerar alltid URL- och lokallagrade cup-id:n mot serverns aktuella behörighetslista.
- Ersätter ogiltiga eller indragna cupval med en behörig cup och uppdaterar URL:en.
- Visar korrekt ägarinformation i admin i stället för att felaktigt påstå att åtkomsten kommer från `tournament_members`.

Ingen databasmodell, cupdata eller arrangörsbehörighet ändras.
