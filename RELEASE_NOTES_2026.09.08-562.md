# CupNavi v562 – Mina cuper

## Varför
Efter inloggning behövde arrangören först välja mellan "Skapa" och "Administrera" och därefter välja cup. När samma konto kan äga eller administrera flera cuper blir det onödigt omständligt.

## Nytt
- Admin öppnar nu på **Mina cuper** i vald miljö.
- Listan är fortfarande server-side filtrerad av medlemskap och Test/Skarp miljö.
- Varje cup visar användarens roll: **Ägare**, **Lokal admin** eller **Driftadmin**.
- Status och cupdatum visas direkt på kortet.
- Live-cuper prioriteras av den befintliga sorteringen.
- **Öppna →** går direkt in i vald cup utan ett extra bekräftelsesteg.
- Snabbknappar för **Skapa ny cup** och **Visa som lista** finns kvar.
- Tom miljö förklarar att användaren kan skapa cup eller byta miljö i vänsterflanken.

## Säkerhet
Ingen ny klientfiltrering introduceras. Organizer-konton får fortfarande endast rader via `tournament_members`, och miljöfiltreringen sker i SQL innan dashboarden renderas.
