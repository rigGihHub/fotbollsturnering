# CupNavi v409 – Team no-show impact preview

Version: `2026.09.03-412-PUBLICATION-FLOW-ORDER`

## Why
A team that has not checked in close to kickoff is one of the most disruptive real match-day situations. The organiser needs to know the blast radius before changing anything.

## Changes
- Cupdagen readiness alerts now offer **Analysera om laget uteblir** for missing team check-ins.
- CupNavi previews every remaining direct team match affected, the number of opponents involved, and the exact upcoming match slots.
- The recommendation is intentionally conservative: keep the slots until the absence is confirmed, then decide walkover/cancellation/rescheduling according to the competition rules.
- No match, score, walkover or schedule is changed automatically.
- The preview reuses the already-loaded Cupdagen match snapshot and adds no database query.
- New pure helper `build_team_no_show_impact_preview` keeps the impact analysis testable outside Streamlit.
