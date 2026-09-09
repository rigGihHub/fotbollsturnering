# CupNavi v1.247 – Public + Team Portal Mobile QA

## Scope
Focused mobile QA for the two views most likely to be used from a phone during a cup:
the public tournament view and the team/participant portal.

## Changes
- Streamlit tab bars are horizontally scrollable on narrow screens and tab touch targets
  remain at least 44 px high. This prevents later tabs such as statistics/messages from
  becoming inaccessible when labels do not fit.
- The team portal login state is compact text instead of a large success alert.
- The first team-portal tab is renamed **Lag & matcher** and starts with task-oriented
  guidance rather than a redundant `Lagstatus` heading.
- Normal states such as disabled check-in and unconfirmed kits use low-emphasis captions
  rather than info alerts.
- Public headline metrics use a 2×2 grid on phones instead of four cramped columns.
- Public match cards receive tighter phone spacing.

## Preserved
Authentication, participant-code verification, unread-message badge logic, check-in and
kit optimistic concurrency, roster/player integrity, match-roster handling, public match
data and public navigation behavior are unchanged.
