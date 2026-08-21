# CupNavi 2026.08.21-90-PERFORMANCE

Fokuserad prestandaoptimering:
- Schema/migrationer körs en gång per Streamlit-process via st.cache_resource, i stället för för varje ny besökarsession.
- Publikvyn använder ett segmenterat sektionsval i stället för Streamlit-tabs, så bara vald sektion renderas.
- Matchhändelser hämtas först när Resultat öppnas.
- Väderprognos är opt-in och externa Open-Meteo-anrop görs inte vid normal sidladdning.
- Delningspanel och QR-kod byggs först när användaren klickar Dela cupen.
- QR-PNG cacheas.
- Vanliga team:<id>-källor löses från redan inläst lagdata i publikvyn, vilket minskar extra DB-anrop.
