# CupNavi v.1.205 – Public Matches Decomposition Phase 2

## Public match filters
Reusable filtering and sorting logic is moved to
`cupnavi_core/public_match_filter_logic.py`.

The Streamlit UI still owns which filter controls are shown, but age class,
group, team and pitch filtering now use pure testable functions.

## Admin progressive disclosure
The optional information fields for:
- Medical readiness
- Lost & found
- Accessibility information

are only rendered when the corresponding feature checkbox is enabled.

When a feature is unchecked, its previously saved text is retained rather than
cleared. Re-enabling the feature restores the saved information.

No schema, permission, lifecycle, scheduling or result logic is changed.
