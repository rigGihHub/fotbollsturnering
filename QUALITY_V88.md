# CupNavi 2026.08.21-88-CI-CLEANUP

- CI-testet kräver inte längre att gamla historikfiler redan har raderats ur GitHub-repot.
- Gamla `UX_V*.md` och äldre `QUALITY_V*.md` ingår inte i releasepaketet.
- Endast aktuell QUALITY-fil följer med.
- Appfunktionaliteten från v87 är oförändrad.
- För att faktiskt radera redan trackade historikfiler ur GitHub måste de tas bort i repot en gång; att ladda upp en ZIP tar inte bort befintliga filer.
