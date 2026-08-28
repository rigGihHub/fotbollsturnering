# CupNavi v1.244 – Final Simplification Audit

## Purpose
This release reviews the simplification passes as one product instead of treating each
admin page independently.

The goal is not to remove working tournament functionality. It is to remove duplicated
presentation and make the overall administration feel like one coherent workflow.

## Implemented changes

### 1. Global admin context is compact
Previously every admin page received a large global context card containing:
- workflow step;
- page title;
- explanatory copy;
- publication state;
- schedule state;
- result state.

Most pages then repeated the same title and purpose in their own header.

v1.244 removes the duplicated global page title and explanatory text. Primary workflow
pages retain only a compact step/status strip.

Secondary tools no longer receive the main workflow status strip.

### 2. Recommended next step is contextual
The global **Nästa steg** action is now shown only on pages that belong to the primary
workflow. Secondary tools no longer compete with their own task by showing an unrelated
workflow CTA.

The recommendation engine and target logic are unchanged.

### 3. Search no longer precedes navigation
**Sök i cupen** remains available, but now appears after the admin navigation rather than
before the five main admin areas. Normal navigation therefore comes first.

### 4. Navigation language is shorter and more consistent
Visible labels were simplified without changing routes:
- Cupinställningar → **Inställningar**
- Matcher och resultat → **Resultat**
- Önskemålscentral → **Önskemål**
- Problem & lösningar → **Problem**
- Instruktioner → **Guide**
- Cupverktyg → **Verktyg**
- Partners & erbjudanden → **Partners**
- Tabell & statistik → **Tabeller & statistik**

The underlying page names and functionality remain intact.

## Primary workflow retained
1. Översikt
2. Lag
3. Grupper
4. Schema
5. Resultat
6. Tabell
7. Slutspel

No route was removed from the workflow.

## Measured source-level control counts
These are static source counts, not claims about controls visible on one screen.

| Control type | v1.243 | v1.244 |
|---|---:|---:|
| Buttons | 79 | 79 |
| Expanders | 76 | 76 |
| Tabs | 5 | 5 |
| Selectboxes | 37 | 37 |
| Checkboxes | 30 | 30 |
| Info/warning/success/error calls | 301 | 301 |

The source-level counts are intentionally almost unchanged in this audit: v1.244 focuses
on hierarchy and timing of existing controls rather than deleting established capability.

## Preserved
- tournament creation and setup;
- competition classes;
- teams, groups and rosters;
- schedule generation and validation;
- results and match events;
- standings and playoffs;
- referee and functionary administration;
- team portal and messaging;
- sponsors/offers;
- visitor analytics;
- import;
- publication blockers and warning approval;
- optimistic concurrency safeguards;
- audit/undo;
- backup/restore and destructive-action protection.

## Follow-up
After v1.244, further simplification should be driven by observed user friction or
browser/user testing rather than continuing to hide controls simply to reduce counts.
