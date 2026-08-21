# CupNavi 2026.08.21-72-STABILISERING1

Fokus: driftsäkerhet och teknisk grund.

- Versionsstyrda databasmigreringar införda.
- Prestandaindex på centrala tabeller.
- Teknisk hälsokontroll under Admin → Kontroller.
- Portabel JSON-backup för vald turnering.
- Runtime- och dev-beroenden separerade.
- CI kör `pip check`, kompilerar alla Pythonfiler, kör pytest samt migrations- och backup-smoketester.
- Arkitekturprinciper dokumenterade.
- Ingen avsiktlig förändring av turneringsflöde eller publik funktionalitet.
