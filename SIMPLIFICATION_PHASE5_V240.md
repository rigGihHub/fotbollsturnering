# CupNavi v.1.240 – Simplification Phase 5

## Scope
This pass simplifies:
- Matcher & resultat
- Domare

No result logic, concurrency protection, publication behavior or referee assignment
logic was removed.

## Matcher & resultat

### Primary task first
The page now prioritizes the result editor instead of showing the full match schedule
before the user can reach the actual work.

The normal flow is:
1. see result progress;
2. register/edit scores;
3. adjust referee on the same row when needed;
4. automatic save.

### Progressive disclosure
The following remain available but no longer occupy the default view:
- **Visa hela matchschemat**
- **Kommande slutspelsmatcher** waiting for resolved teams
- **Regler vid oavgjort i slutspel**

Publication state is shown as compact context at the top instead of success/warning
boxes both above and below the editor.

### Preserved safeguards
- incomplete score pairs are not silently saved;
- result writes still use `update_match_result_if_unchanged()`;
- stale concurrent edits remain protected;
- published matches still receive `schedule_published=1`;
- feed items and team notifications remain unchanged;
- playoff penalties/deciding-winner logic is preserved.

## Domare
Adding a referee now asks only for **Namn** in the default form.

Optional:
- phone;
- email

are under **Kontaktuppgifter**.

The full referee/contact table is under **Visa domarlista & kontaktuppgifter**.
A compact count remains visible so Admin can see whether referees exist.

Email validation and persistence are unchanged.

## Test contracts
Legacy source-string tests were updated where they required the old explanatory copy.
They still verify autosave, public result synchronization and the result progress state.
