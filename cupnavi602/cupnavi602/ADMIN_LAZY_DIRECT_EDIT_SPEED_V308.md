# CupNavi v1.308 – Admin lazy direct edit speed

## Mål
Förenkla Adminöversikten och undvik avancerade cup- och regelqueries när direktredigeringen inte används.

## Ändring
- Direktredigera cupinställningar laddas nu först efter aktivt val via `Visa direktredigering av cupinställningar`.
- `schedule_rules`, aktuell lagräkning och historikskyddets beroenden körs därför inte i standardläget.
- När direktredigering öppnas visas den befintliga sektionen expanderad och all tidigare funktionalitet finns kvar.
- Ingen schema-, resultat-, publicerings-, auth-, DB-schema- eller concurrencylogik har ändrats.

## Effekt
Adminöversikten gör mindre read-only-arbete i normalfallet och visar färre avancerade kontroller tills de faktiskt behövs.
