# CupNavi v464 — Public Navigation + Mobile Compatibility Audit

## Mål
CupNavi ska fungera robust på moderna och äldre mobiltelefoner, inte bara på en enskild Android-bredd.

## Viewport-matris
CSS och källkontrakt är nu uttryckligen säkrade för följande representativa CSS-bredder:
- 320 px — små/äldre iPhone och Android
- 360 px — vanlig mindre Android
- 375 px — vanlig iPhone-bredd
- 390 px — moderna iPhone-modeller
- 412 px — vanlig större Android
- 430 px — större iPhone
- upp till 768 px — telefon/kompakt tablet-portrait

## Förbättringar
- Fem publika huvudval ligger kvar på en rad även på 320–360 px.
- Separata regler för ≤430, ≤360 och ≤330 px.
- Minsta touchyta 44 px i huvudnavigationen och kärnkontroller.
- Safe-area för vänster/höger/top/botten för notch, Dynamic Island och home indicator.
- 16 px formulärtext på mobil för att motverka oönskad iOS-zoom vid fokus.
- `text-size-adjust` stabiliseras så browsern inte förstorar enskilda textblock oförutsägbart.
- Bilder, SVG, video och canvas kan inte bli bredare än viewport.
- Popovers använder `100dvh` för bättre beteende med mobilens dynamiska browserfält.
- Små matchkort komprimeras ytterligare under 360 px utan att lag/tid/plan tappas.

## Viktig begränsning
Det går inte att lova bokstavligen varje telefonmodell och varje webbläsarversion utan fysisk/browserfarm-testning. v464 bygger därför på responsiva standards, representativa viewport-bredder och automatiserade källkontrakt. Skarpt genrep på riktiga telefoner är fortfarande slutlig produktionsgate.

## Prestanda och säkerhet
Ingen ny DB-fråga, ingen resultatskrivning och ingen schemaändring. Schema v32.
