# CupNavi v445 – Route performance budgets

## Varför
Efter v439–v444 har många dubbel-reruns och onödiga DB-rundresor tagits bort. Nästa risk är att nya funktioner gradvis lägger tillbaka arbete på de viktigaste vyerna utan att det märks i kodgranskning.

## Ändring
- Inför mjuka prestandabudgetar för de mest använda publika och administrativa rutterna.
- Separata budgetar för första rendering och varm rerun.
- Budgeten följer både total renderingstid och antal DB-anrop.
- En långsam nätverksanslutning blockerar aldrig appen: budgeten är diagnostik, inte ett runtime-fel.
- Adminöversiktens prestandapanel visar om de senaste rutterna ligger inom budget.
- Structured performance-logg innehåller budgetstatus så Cloud-loggar kan följas över tid.
- Performance Contract kräver att kärnrutterna fortsatt har explicita budgetar.

## Kärnrutter
- Turneringsvy / Info
- Turneringsvy / Matcher
- Turneringsvy / Mitt lag
- Admin / Adminöversikt
- Admin / Lag
- Admin / Grupper
- Admin / Skapa och publicera schema
- Admin / Kontroller
