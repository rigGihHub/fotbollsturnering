# CupNavi v1.271 – Cold-start fast path

## Syfte
Minska arbete som görs på varje Streamlit-start/rerun innan den publika vyn kan visas, utan att ändra cupflöden eller dataintegritet.

## Ändringar
- Källfingeravtrycket läser inte längre innehållet i alla Pythonfiler vid varje rerun. `VERSION.txt` läses som release-markör och övriga källfiler bidrar med path/size/mtime-metadata.
- PDF/exportmodulen (ReportLab) lazy-loadas först när en PDF faktiskt skapas.
- AI-truppimport lazy-loadas först på Admin → Spelare & trupper när funktionen används.
- CSV/Excel-importservice lazy-loadas först på importsidan.
- QR-biblioteket lazy-loadas först när en QR-kod behöver genereras.

## Risk / kompatibilitet
Ingen databas- eller schemaändring. Ingen ändring av concurrency-skydd. Hot-deploy-detektion behålls genom versionsfil + filmetadata. CupNavi-processen förutsätter fortsatt att varje release höjer VERSION.txt.

## Verifiering
Riktade kontraktstester säkerställer versionssynk, metadata-baserat fingerprint och att tunga/sekundära moduler inte längre importeras globalt i app.py.
