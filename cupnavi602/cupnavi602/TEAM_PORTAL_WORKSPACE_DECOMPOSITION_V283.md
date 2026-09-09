# CupNavi v1.283 – Team portal workspace decomposition

Version: `2026.08.29-285-SCHEDULE-WORKSPACE-DECOMPOSITION`

## Syfte

Fortsätta den stegvisa minskningen av `app.py` utan att flytta eller förenkla de concurrency-känsliga skrivoperationerna.

## Ändringar

- Flyttat lagportalens Streamlit-orkestrering till `cupnavi_core/team_portal_view.py`.
- Infört `TeamPortalDependencies` så att portalen använder injicerade writers från `app.py`.
- Flyttat read-only portalfrågor till `cupnavi_core/team_portal_repository.py`:
  - lag/deltagare,
  - access credential,
  - mottagna/skickade meddelanden,
  - lagets matcher,
  - spelartrupp,
  - matchtrupper.
- `render_team_portal()` i `app.py` är nu en tunn kompositionsgräns.
- Befintlig inloggning, check-in, matchställ, kontaktperson, spelartrupp, matchtrupp och interna meddelanden är bevarade.
- Befintliga source-contract-tester har uppdaterats till den nya modulgränsen.

## Integritet

Följande writers ligger fortsatt i `app.py` och injiceras till view-lagret:

- `_set_team_checkin_if_unchanged`
- `_confirm_team_kit_if_unchanged`
- `_save_team_contact_if_unchanged`
- `_add_team_player_if_capacity`
- `_update_team_player_if_unchanged`
- `_delete_team_player_if_unchanged`
- `_save_match_roster_if_unchanged`
- `_send_team_message`
- `_mark_team_messages_read`

Ingen DB-schemaändring eller migration ingår.

## QA

Fokuserat regressionstest: `tests/test_v283_team_portal_workspace_decomposition.py` plus befintliga lagportal-, privacy-, messaging- och batchingkontrakt.

Full teststatus dokumenteras i releaseleveransen efter körning.
