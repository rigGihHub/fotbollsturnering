# CupNavi v548 – Reporter Network Resilience

- Tydlig sparstatus i rapportörens CupNavi Score: **Sparar…**, **Sparat**, **Sparstatus osäker** och **redo**.
- Browserbaserad nätindikator visar **Online** eller **Dåligt nät / offline** direkt i live-rapporteringen.
- Vid osäker skrivning sker fortfarande ingen automatisk retry. Rapportören måste först läsa om serverläget, vilket skyddar mot dubbelregistrering.
- Befintliga atomiska måltransaktioner och optimistic locking behålls som server-side skydd.
- Befintligt lokalt offlineutkast finns kvar som reserv när nät saknas.
- v547 stora resultattavla och setup-styrda målskytt/assist/kort behålls.
