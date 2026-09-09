# CupNavi v565 – Decision-driven Admin Overview

## Syfte
Göra Adminöversikten mindre till en statuspanel och mer till ett beslutsstöd för en ovan cupadministratör.

## Förändringar
- Ny gemensam beslutsmodell som alltid svarar på tre frågor: vad gör jag nu, vad saknas före publicering och är cupen faktiskt redo att publiceras.
- Adminöversiktens primära kort använder nu nästa verkliga blockerande steg, inklusive Cupinfo, lag, grupper, regler, planer/tider och schema.
- Oplacerade lag håller Grupper ofärdigt i stället för att översikten går vidare för tidigt.
- En ren grundsetup märks inte som publiceringsklar förrän den fullständiga Kontroll-valideringen faktiskt har körts och är färsk.
- Om en färsk Kontroll-snapshot är ren visas tydligt “Cupen är redo att publiceras”.
- Blockerande valideringsfel skickar användaren direkt till Kontroll.
- “Det här saknas före publicering” visar högst fyra konkreta åtgärder med direktknappar; resterande steg följer därefter i rätt ordning.
- Sekundära uppmärksamhetsnotiser dedupliceras mot samma sak i den nya checklistan.
- Första-cup-hjälpen uppdaterad från den gamla 7-stegsmodellen till dagens 9 steg, inklusive Regler och valfria Domare.
- Visuell statusmarkering för nästa-steg-kortet: neutral, varning eller klar.

## Säkerhet/prestanda
- Adminöversikten startar inte den dyra fullständiga schemavalideringen. Den använder endast en redan känd färsk snapshot; annars skickas arrangören till Kontroll.
- Ingen publiceringsstatus eller cupdata ändras automatiskt.
- Existerande skydd för importerade/befintliga scheman och spelade resultat påverkas inte.
