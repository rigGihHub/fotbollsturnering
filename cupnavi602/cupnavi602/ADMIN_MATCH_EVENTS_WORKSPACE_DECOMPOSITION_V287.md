# CupNavi v287 – Admin Matchhändelser workspace decomposition

Version: `2026.08.29-287-ADMIN-MATCH-EVENTS-WORKSPACE-DECOMPOSITION`

## Ändrat
- Flyttar adminytan **Matchhändelser** från `app.py` till `cupnavi_core/admin_match_events_view.py`.
- Flyttar read-only-frågor för spelade matcher, spelare och spelarstatistik till `cupnavi_core/admin_match_events_repository.py`.
- Återanvänder befintliga rena projektioner för eventrader och feature-styrda kolumner.
- Behåller `update_player_match_stats_if_unchanged` och transaktionen i `app.py` via en smal save-callback.
- Bevarar autosave, mål/assist-validering och konfliktfeedback.

## Riskgräns
Ingen schema-, auth- eller migrationsändring. Optimistic locking för spelarhändelser ligger kvar i applikationsgränsen.

## Verifiering
Se releaseleveransen för faktisk teststatus. Browser-E2E, fysisk mobil och live-deployment ska inte antas verifierade om de inte uttryckligen körts.
