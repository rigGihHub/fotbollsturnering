# CupNavi 2026.09.10-614-MATCHDAY-FAVORITES-PWA

- Next.js publikvy öppnar nu i en riktig Matchday-startsida i stället för en generell matchlista.
- Flera favoritlag kan väljas och sparas lokalt per cup; befintligt team-summary-API används för placering och spelade matcher.
- Matchday lyfter nästa match för favoritlag före övriga matcher, med tid, plan och befintlig tröjfärgsvisualisering.
- Mobil bottom navigation införs för enhandsgrepp på cupområdet.
- Publik data uppdateras lättviktigt var 30:e sekund utan full sidladdning.
- PWA-foundation: manifest, ikon, service worker och installationsbar standalone-yta.
- Notisberedskap: användaren kan ge webbläsaren notisbehörighet från Matchday. Full push-backend ingår inte i v614.
- Streamlit lämnas fortsatt orörd och är fortfarande liveversionen.
