# v371 – Riktig matchstatus

- Matcher har nu explicit status: Ej startad, Pågår, Paus och Slut.
- Matchrapportören kan ändra status direkt i CupNavi Score.
- Cupdagen använder explicit status som sanningskälla och gissar inte att en match pågår bara för att starttiden passerats.
- Cupdagen kan starta, pausa, återuppta och avsluta matcher.
- Publika matchkort visar PÅGÅR/PAUS/SLUT från samma statusmodell.
- Publika liveflödet använder samma explicit status.
- Mitt lag behandlar en aktiv match som aktuell även om schemalagd starttid passerats.
- När ett slutresultat sparas markeras matchen automatiskt som Slut.
- Statusändringar använder optimistisk låsning så en gammal vy inte skriver över en nyare status.
- Faktisk start- och sluttid sparas när status ändras.
- Schema v30 lägger till match_status, status_updated_at, actual_started_at och actual_finished_at.
- Äldre in-memory snapshots utan statusfält behåller tidigare tidsbaserade fallback för bakåtkompatibilitet; riktiga v371-databasposter använder explicit status.
