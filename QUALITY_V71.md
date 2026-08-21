# CupNavi 2026.08.21-71-WEBTEST

CI-fix:
- `pypdf` tillagt i requirements.txt eftersom test_pdf_export.py importerar PdfReader från pypdf.
- Regressionstest säkerställer att både pypdf och reportlab finns deklarerade.
- Appversion uppdaterad till 71.
