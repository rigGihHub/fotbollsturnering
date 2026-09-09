# CupNavi v587 – UI/UX expert review of the organizer flow

## Goal
Make the nine-step preparation journey feel like one continuous job, not a collection of admin pages.

## Findings implemented in v587

### 1. Two competing nine-step navigators
The global admin shell already keeps all nine steps accessible. Several workspaces rendered the full same flow again inside the page. This consumed the first screen and made it unclear which navigator was authoritative.

**Change:** the global flow is authoritative. The legacy workspace helper stays available for isolated rendering/tests but suppresses itself when the global shell has already rendered.

### 2. Kontroll and Publicera could show the wrong active step
Both steps intentionally share the `Kontroller` backend route. The route-to-step dictionary therefore collapsed the duplicate route to the last value (`Publicera`). An organizer on Kontroll could see Publicera highlighted in the global flow.

**Change:** the visible step is now resolved from `planning_control_focus_{tid}`. Choosing Kontroll/Publicera in the global flow sets that focus explicitly.

### 3. Back from Kontroll used a non-existent route
The button `← Till Schema` used `Schema`, while the real admin route is `Skapa och publicera schema`.

**Change:** it now uses the real route and returns to Schema reliably.

### 4. Revised source material was hidden under participant import
A new/changed PDF or photo can change rules, pitch windows, groups and the schedule. Treating Import as a participant-only destination gives the wrong mental model.

**Change:** Import is now a cup-wide/overview workspace and Adminöversikt has a clear `🔄 Ny eller ändrad PDF / foto` shortcut.

## Flow after v587
1. Cupinfo
2. Lag
3. Grupper
4. Regler
5. Planer & tider
6. Domare (optional)
7. Schema
8. Kontroll
9. Publicera

`Förbered cupen` and `Cupdagen` remain separate work modes. `Övrigt` and `Åtkomst & koder` remain outside the numbered flow.

## UX priorities for the next passes

### A. Adminöversikt should become shorter
It still contains too many secondary analyses and operational details. The first screen should contain only:
- current state,
- one recommended next action,
- blockers,
- changed-source shortcut.
Everything else should progressively disclose.

### B. Each setup step should end in one clear handoff
There are still pages with several competing lower-page actions. The target pattern should be:
- save/confirm the current task,
- one primary `Fortsätt till …`,
- one secondary `Tillbaka`.

### C. Schema needs a clearer three-state model
The organizer should immediately understand one of:
- CupNavi creates the schedule,
- imported schedule is being reviewed,
- existing schedule is being edited.
Advanced repair/import tools should appear only after one of these paths is chosen.

### D. Revision import should become a guided mini-flow
For a changed PDF/photo the ideal sequence is:
1. Läs in
2. Vad har ändrats?
3. Konsekvenser
4. Godkänn
5. Kontrollera schemat
This should feel like one task rather than several independent sections on the Import page.

### E. Cupdagen should never inherit setup density
Operational actions must stay above setup/navigation detail when the cup is live. The current two-mode model is correct; next QA should focus on first-screen density on a phone.
