# CupNavi v.1.221 – Team Portal Performance Audit

Target: `render_team_portal`, a 310-line participant/team portal render path.

Changes:
- player roster is loaded once per portal render and reused by Matchtrupper;
- previous-match roster detection is one DISTINCT query instead of one COUNT query per earlier match;
- team-match lists now prefilter direct `team:<id>` sources in SQL while retaining unresolved playoff/group sources for correctness.

Impact:
- removes one duplicate player query per authenticated portal render;
- replaces an O(previous matches) database-query loop with one query;
- reduces rows passed through Python source resolution for normal direct-team group matches.

No permissions, roster mutation semantics, deadline rules, messaging, check-in, or result reporting behavior is changed.
