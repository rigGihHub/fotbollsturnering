# CupNavi v1.246 – Mobile Journey QA

Focused QA of the organizer journey from creating a cup toward a publishable schedule,
with particular attention to narrow Android/iPhone layouts.

## Changes
- Admin Streamlit columns may wrap on screens <=768 px instead of being forced into
  cramped desktop-width columns.
- On screens <=390 px admin columns stack to full width.
- Workflow status pills wrap instead of overflowing horizontally.
- Tournament creation now tells the organizer what happens immediately after Create,
  without adding another form step.
- Team registration count is normal contextual status rather than an info alert.
- The primary schedule action uses short labels suitable for mobile:
  **Skapa hela spelschemat** / **Uppdatera återstående schema**.
  The important preservation behavior for played matches is retained as supporting text.

## Preserved
No scheduling, publication, competition-class, team-limit, result or concurrency behavior
was changed. Touch targets remain at least 44 px in the existing responsive system.
