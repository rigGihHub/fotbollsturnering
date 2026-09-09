# CupNavi v.1.229 – Technical Cleanup & Dead Code Audit

## Verified dead code removed
The old HTML/JavaScript share implementation had been superseded by the integrated
Streamlit popover but remained in app.py.

Removed:
- `share_panel_html()` — 113 lines
- `render_share_panel()` — 2 lines
- `qr_share_panel_html()` — 134 lines
- `render_qr_share_panel()` — 4 lines
- two CSS-only legacy anchor selectors

Total verified dead Python removed: 253 lines.

Repository-wide search showed the four functions had no runtime call sites. The only
remaining references were historical source-contract tests, which are now updated to
test the live integrated share popover instead.

## Safety checks
The active public share implementation remains:
- Streamlit `st.popover("Dela")`
- current cup URL
- WhatsApp
- email
- SMS
- QR generation/download

Analytics helpers and `qr_png_bytes()` were explicitly retained.

## Static audit result
After removal:
- no unused imports are detected in app.py by AST name usage;
- no unreferenced public top-level functions remain under the same static criterion.

This release intentionally does not remove private helpers based on reference count
alone because decorators, callbacks and indirect use make that less safe.
