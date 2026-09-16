# CupNavi v2.6.92

- Mobil-PWA-testet kör nu den aktuella Next.js-rapportörsvyn i stället för den gamla statiska `public_pwa`-klienten.
- E2E-testet verifierar på Pixel- och iPhone-profiler att ett resultat sparas i den beständiga offlinekön och finns kvar efter offline-omladdning.
- Webbläsarmatrisen testar nu Next.js i Chromium, Firefox och WebKit; det gamla Streamlit-smoketestet blockerar inte längre produktionsreleaser.
- Offline-, touch- och prestandaförbättringarna från v2.6.90 är oförändrade.
