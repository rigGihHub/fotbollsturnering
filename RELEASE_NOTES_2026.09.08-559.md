# CupNavi v559 – Environment Switch & Public Production Safety

- Added an always-visible Admin sidebar switch between Testmiljö and Skarp miljö.
- Admin tournament lists are filtered server-side by selected environment.
- Switching environment clears the active cup selection to prevent cross-environment mistakes.
- New cup creation follows the currently selected Admin environment by default.
- Public tournament discovery only exposes production tournaments.
- Direct public `?cup=` links also reject test-environment tournaments.
- Production mode shows a visible warning in the sidebar.
