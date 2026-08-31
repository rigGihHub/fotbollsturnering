# CupNavi v325 – Admin mobile simplification

## Goal
Reduce cramped controls and unnecessary visual density in the organizer's two most common mobile entry points without changing tournament logic or persistence.

## Changes
- Replaced the five-column top-level Admin area button row with one native `st.segmented_control`.
- The selected Admin area still opens its first logical page and all existing pages remain reachable.
- Simplified the Setup sport profile from four narrow metric cards to one compact summary line.
- Moved creation of a competition class into a progressive `Lägg till tävlingsklass` expander, automatically open while no class exists.
- Competition class editing now uses vertical bordered cards instead of five compressed columns. Planned teams, level and removal remain available with the same persistence rules.

## Safety
No changes to schedule generation, results, playoff logic, team/player integrity, authentication or concurrency controls.
