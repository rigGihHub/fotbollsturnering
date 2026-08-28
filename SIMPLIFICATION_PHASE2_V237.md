# CupNavi v.1.237 – Simplification Phase 2

## Scope
This release simplifies two high-density Admin areas without removing functionality:
- Cupinställningar
- Schema

## Cupinställningar
Before:
- release diagnostics,
- sport profile,
- format recommendation,
- phase/change matrix,
- change-impact selector,
- primary setup action

were all presented in the same page flow.

Now:
- current phase remains visible;
- **Ändra cupens inställningar** is the dominant primary action;
- technical release information stays behind its existing collapsed expander;
- phase rules + impact preview are grouped under
  **Kontrollera konsekvens före större ändring**.

The change-impact functionality remains available, but no longer competes with the
normal task of editing cup settings.

## Schema
The everyday flow is now:
1. see status;
2. create/update the schedule;
3. react to blocking issues.

Secondary information is progressively disclosed:
- **Regelverk & schemakvalitet**
- **Detaljer per grupp**
- **Exportera schema**
- **Reseinformation**

Existing visual schedule, drag-and-drop and adjustment tools remain available.

## Removed visual noise
- long always-visible saved-rule explanation;
- four schedule-quality metrics from the default view;
- group diagnostics table from the default view;
- PDF instructions from the default view;
- travel-information table from the default view;
- broad explanatory info box that duplicated information available in Kontroller.

## Preserved
- schedule generation and regeneration;
- protection of played matches;
- validation and recovery;
- playoff generation;
- PDF export;
- travel preferences;
- visual schedule;
- drag-and-drop;
- conflict checks;
- all persistence and concurrency protections.

No backend model or scheduling rules were changed.
