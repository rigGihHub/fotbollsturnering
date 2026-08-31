# CupNavi v328 — Mobile tournament switcher

## Problem
On desktop the active tournament selector is in Streamlit's sidebar. On phones the sidebar is normally collapsed, so an administrator could create a tournament from the main flow after v327 but still had no equally direct way to switch between existing tournaments.

## Change
- Admin now exposes a compact `🏆 Turnering · …` expander in the main content area.
- The expander contains `Byt aktiv turnering` and uses the same tournament labels as the desktop sidebar.
- The main selector owns a separate Streamlit widget key and synchronizes through a callback into the canonical `active_tournament_selector` and `preferred_tournament_id` state.
- The existing sidebar selector remains unchanged for desktop users.
- Existing canonical `cup=` URL synchronization runs after selection resolution, so a mobile change follows the same deep-link behavior as desktop.
- v327's mobile `Ny turnering` path remains directly below the switcher.

## Safety
No database writes are added by switching tournaments. Tournament creation, authorization, lifecycle, scheduling, results and concurrency logic are unchanged.
