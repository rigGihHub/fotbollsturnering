# CupNavi v.1.233 – E2E Submit Hardening

## Failure addressed
The active-tournament-switch E2E occasionally failed because Playwright reported
`submit.click(force=True)` as successful while Streamlit never accepted the form
submit. Waiting longer for SQLite could not fix a submit event that never happened.

## Fix
The create helper now:
- reacquires the visible create form for every submit attempt;
- verifies/refills tournament name and location after any rerender;
- verifies Testmiljö is still selected;
- reacquires the actual `Skapa` button;
- invokes its DOM click, avoiding Streamlit pointer-interception/animation races;
- waits for either real SQLite persistence or the post-create UI signal;
- retries once only when neither signal appears.

The test still creates the tournament through the real Streamlit UI. No direct DB
insert or weakened assertion is used.

## Regression contracts
Older source-contract tests that required the previous `force=True` implementation
were updated to require the stronger submit behavior instead.

v1.232 delayed-persistence polling and public fresh-read protection remain intact.
