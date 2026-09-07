# CupNavi 2026.09.07-494-PUBLIC-UX-PDF

## Public UX + PDF

- Väderprognos är på som standard på Matchersidan och lämnar inte längre ett tomt utrymme när prognos saknas.
- Målskyttar/kort är på som standard när individuell matchstatistik är aktiverad för cupen.
- Alla grupptabeller är öppna som standard på Tabellsidan.
- PDF har flyttats in under **Dela** och använder Streamlit 1.61:s deferred download-data: ett klick skapar och laddar ned PDF-filen direkt.
- PDF-byggaren verifierar `%PDF`-signaturen innan filen lämnas till webbläsaren.
- Informationsskärm har flyttats in under **Dela** i stället för att ligga frikopplad ovanför Cupinfo.
- Cupinfo har fått tydligare visuell hierarki och robustare kortlayout för platser/praktisk information.
- Vänsterflanken har fått en kompakt Text-TV/future-inspirerad kontrollpanel med tydligare rubrik, val och avgränsning.

Ingen ändring av schema-, resultat-, slutspels- eller transaktionslogik.
