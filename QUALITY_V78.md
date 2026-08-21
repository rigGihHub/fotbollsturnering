# CupNavi 2026.08.21-78-REPORTER

- Publika Matchcenter har tagits bort helt.
- Ny separat roll: Matchrapportör.
- Matchrapportören har egen inloggning och kommer endast åt Resultat och Matchhändelser.
- Standardlösenord för Matchrapportör är `123`.
- Lösenordet kan senare ersättas via Streamlit Secret `MATCH_REPORTER_PASSWORD`.
- Matchrapportören kan inte skapa turnering, ändra schema, lag, grupper, domare, sponsorer eller övriga admininställningar.
- Resultat och giltiga matchhändelser sparas automatiskt.
