# CupNavi v.1.194 – Genomförd rensning

1. En enda `_set_view_mode()` är nu sanningskälla; direct-link/cup-URL-logiken kan inte längre skrivas över av en senare definition.
2. Den gamla oanvända `render_empty_state()` är borttagen; den semantiska versionen med `role=status` behålls.
3. Admin-navigationen visar bara kärnsidor direkt. Situationsbundna sidor ligger under **Fler verktyg** och expanderas automatiskt om en sådan sida är aktiv.
4. Föregående/nästa-knapparna i Admin-flödet är borttagna. Den kontextuella **Nästa rekommenderade steg** är enda dominerande flödes-CTA:n; fri navigering sker via områdesnavigationen.
5. Databasbackend visas inte längre i normal sidebar.
6. Redundant hjälptext under "Följ mitt lag" visas inte när inget lag är valt.
7. Osäker dead code/CSS har inte raderats; den ligger som UTRED för senare steg med visuell regression.

## Verifiering efter rensning
- Full vanlig pytest-svit: PASS.
- `compileall`: PASS.
- Schema contract: PASS.
- PWA installability contract: PASS.
- Health contract: PASS.
- E2E critical journey: 3 browserfall kan samlas in utan syntax-/importfel; full Playwright-matris lämnas till GitHub Actions.
- `_set_view_mode`: 1 definition (tidigare 2).
- `render_empty_state`: 1 definition (tidigare 2).
- 22 Admin-sidor finns kvar; rensningen ändrar synlighet/hierarki, inte funktionell åtkomst.
