# Live review — Slottskampen-6, v2.8.1

User supplied the correct live cup URL: /cup/slottskampen-6.
The former /cup/slottskampen-2 still gives 404. Homepage links now use the current cup.

Observed live in v2.8.0 (browser viewport 500 × 820 CSS pixels):
- 9 teams, 18 matches, 3 initial groups.
- All eight standing columns visible, with Örebro SK's 1 played / 3 points.
- Group tables are separate from gold, silver and bronze placement tables.
- Bromölla team navigation filters to two matches, future match before finished.
- Public schedule and rules use actual saved cup data.

Issues fixed in this stage:
- Public reporting/admin links were absent without an existing admin session.
  Links now preserve cup identity and still lead through normal authentication.
- Unresolved qualifiers rendered fabricated default shirt colours. No team means
  no shirt visual, while qualification labels remain visible.
- Placement tables were followed by an undifferentiated list of all playoff
  matches. Each group now has its own expandable match list. Matches not assigned
  to any placement group remain visible in their original bracket section.
- Active match count used an inherited pale yellow colour on white; uses text
  colour now. Reporter login actions and canvas follow the new design tokens.
- One failed eight-second health request permanently disabled admin login.
  Health is advisory; the existing authenticated login endpoint still decides access.

Validation: production build, matchday/component tests, all-column CSS cascade
at 360/390/430 and desktop widths, placement and reporter-login regressions.
500px browser inspection is not a claim of visual testing at 360/390/430.
Authenticated workflow acceptance remains pending; no new login was attempted
with the previously rejected credentials.
