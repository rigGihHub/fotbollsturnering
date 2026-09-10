# CupNavi 2026.09.10-615-NEXT-VISUAL-RUNTIME-HARDENING

## Varför
Första lokala körningen av Next.js mot riktig Turso-data avslöjade både runtime-friktion och visuell densitet som behövde hårdnas innan första frontend-commit/deploy.

## Ändrat
- Service worker registreras bara i production. I dev avregistreras gamla workers och CupNavi-cache rensas defensivt.
- `themeColor` flyttad från metadata till Next.js `viewport` export.
- Startsidan ersatt med en riktig publik CupNavi-entré istället för utvecklarinstruktion.
- Desktopbredd, hero, navigation, favoriter, nästa-match-kort och lagpass har stramats upp visuellt.
- Nästa match beräknas nu över hela matchlistan och kan inte missas för att första 18 matcher redan är spelade.
- Versionssträngen synkad i `VERSION.txt`, `cupnavi_core/version.py` och `app.py`.

## Verifiering
- Python compileall.
- Fokuserade pytest-tester för Next foundation + v615 runtime hardening.
- ZIP-integritet.
- Next build ska verifieras lokalt på Windows där node_modules redan finns; sandboxen har inget installerat node_modules.

## Känd säkerhetsåtgärd
Turso-token som exponerades i en skärmbild ska roteras innan push/deploy.
