# CupNavi v.1.239 – Simplification Phase 4

## Scope
This pass simplifies:
- Adminöversikt
- Kontroller

The goal is to make the overview answer two questions quickly:
1. What needs attention?
2. What should I do next?

All operational, technical and destructive tools remain available.

## Adminöversikt

### Default view
The main page continues to show:
- current mode;
- preparation progress;
- attention items;
- next recommended step;
- high-level cup status.

### Moved behind progressive disclosure
The following areas remain available but no longer compete in the default hierarchy:
- **Förberedelser i detalj**
- **Driftstatus** (opens automatically on cup day)
- **Genvägar & publik vy**
- **Direktredigera cupinställningar**
- **Publicering & startkontroll**
- **Riskzon – Cup och papperskorg**
- **Testverktyg**

The large direct-edit form is intentionally secondary because normal rule changes
already have a dedicated Cupinställningar flow.

## Kontroller

### New hierarchy
The tournament-domain checks now appear before technical tooling:
- blockerande fel;
- varningar;
- schemalagda matcher.

Blocking errors and warnings remain visible because they directly affect publication.

### Secondary details
- load/rest detail and basic group/team checks are under **Fördjupad kontroll**;
- backup/database health remains under **Teknisk hälsa och backup**;
- mobile checklist and performance diagnostics remain collapsed technical tools.

Technical tools were moved below the actual tournament checks so an organizer does not
have to pass database/backup administration before seeing whether the cup can publish.

## Preserved
- all workflow actions;
- Control Center;
- fairness analysis;
- checklist;
- publication status and validation;
- trash/restore/permanent delete;
- test environment tools;
- backup and restore;
- mobile QA checklist;
- performance diagnostics;
- blocker/warning calculations.

No backend or data-model changes were made.
