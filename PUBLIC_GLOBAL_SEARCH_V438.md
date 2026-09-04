# v438 – Publik global sökning

CupNavi får en Gothia-inspirerad men snabbare och mer fokuserad sökning i den publika cupvyn.

- En sökruta högst upp söker lag, publicerade matcher och planer.
- Sökningen är submit-driven: tangenttryckningar startar inga Streamlit-reruns.
- Info-sidan behåller sin kalla fast path; lag/schema hämtas först när besökaren faktiskt söker.
- Lagträff öppnar Mitt lag.
- Planträff öppnar Matcher filtrerat på planen.
- Matchträff öppnar exakt den publicerade matchen via `?match=`.
- Resultaten byggs från redan använda publika snapshots plus en liten pitch-read.
