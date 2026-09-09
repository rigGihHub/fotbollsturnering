# CupNavi v1.245 – UX/QA Journey

This release follows the final simplification audit with a focused QA pass through the
primary organizer journey.

## Fixed friction

- **Admin overview:** the collapsed start/publication check no longer performs a second
  full schedule validation during the same render. It reuses the validation result already
  prepared for publication controls.
- **Admin overview:** duplicated publication heading, publication metrics and explanatory
  publication box were removed from the collapsed start check. Publication status and the
  actual action remain in the sidebar.
- **Results:** visible page terminology now matches the navigation label: **Resultat**.
  The redundant second-level result heading was replaced by concise guidance.
- **Groups:** competition-class placement guidance is now low-emphasis contextual text.
- **Schema:** two instructional info boxes that did not represent problems were reduced to
  captions, keeping warnings and errors visually dominant.

## Preserved

No tournament domain behavior was removed. Scheduling, validation, publication blockers,
result concurrency, group constraints, PDF generation, audit protections and public output
remain unchanged.

## QA principle

Warnings and errors should signal conditions that need attention. Normal instructions and
secondary explanations should not visually compete with them.
