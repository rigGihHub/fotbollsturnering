# v415 — Public UX & performance

- Flyttar **Info** längst till vänster i publik navigation och kortar etiketten från Information till Info.
- Stabiliserar **Mitt lag**-vyn genom att ta bort dubbel rubrik/överlappande selectbox-label.
- Balanserar publiköversiktens nyckeltal/highlight-kort i en tydligare desktop-grid.
- Lägger 15 sekunders sessionscache på den publika overview-queryn för att undvika onödiga Turso-roundtrips vid snabba reruns och flikbyten.
- Ingen ny designsystemgren; ändringen ligger i befintliga finala style_system.py.
