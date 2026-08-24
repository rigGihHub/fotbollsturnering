# CupNavi v137 – Quality report

Version: 2026.08.24-137-MESSAGING-SCHEDULE-TRAVEL-RECOVERY
Schema: v19

## Implementerat
- Olästa lagmeddelanden visas med röd markering och antal i Lagportalens Meddelanden-flik.
- Meddelanden sparas före e-postförsök. SMTP är konfigurerbart via CUPNAVI_SMTP_* och leveransfel sparas utan att meddelandet förloras.
- Schemaläggningsmål: `earliest_finish` eller `use_pitch_windows`; valet påverkar kandidatobjektivet.
- Varje plan/spelyta kan ha namn och adress.
- Valbar restid mellan planer med explicit minutmatris; schemaläggaren lägger på restid när samma lag byter plan.
- Ny adminsida `Problem & lösningar` samlar olösta schemaproblem, valideringsfel/varningar och befintliga smarta återställningsåtgärder.
- Databasmigration v19 är idempotent och reparerar även sparsamma äldre schemastrukturer.

## Verifiering
- `python -m py_compile app.py cupnavi_core/*.py`: PASS
- `pytest -q`: PASS, 332/332 tester
- Versionssynk app.py / cupnavi_core/version.py / VERSION.txt: PASS
- Releasepaket kontrolleras efter paketering.
