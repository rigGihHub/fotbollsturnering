# v1.275 – Public Team Follow Decomposition

## Syfte
Fortsätta den stegvisa nedbrytningen av `app.py` utan att ändra det publika användarflödet eller lägga till nya beroenden.

## Förändring
- Ny ren modul `cupnavi_core/public_team_follow.py`.
- Urval/sortering av ett favoritlags matcher, nästa/senaste match samt spelade/vunna matcher ligger nu utanför Streamlit-vyn.
- HTML för kortet **Mitt lag** byggs i samma rena modul med explicit escaping.
- `app.py` behåller query-parametrar, Streamlit-widgets, tabelluppslag, vägbeskrivning, prenumerationer och notifierings-DB.
- Ingen schema- eller datamigrering.

## Riskkontroll
Funktionaliteten har flyttats i liten omfattning. Interaktiv state/persistence och DB-skrivningar har inte ändrats.

## Verifiering
Se releaseleveransen för tester som faktiskt kördes. Full fysisk mobiltest och deployed browser-E2E räknas inte som verifierade om de inte uttryckligen körts.
