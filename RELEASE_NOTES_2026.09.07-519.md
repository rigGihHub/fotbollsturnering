# CupNavi v519 — Beginner E2E Regression

- Moderniserar historiska UI-regressionstester så de testar dagens sjustegsflöde i stället för borttagna fem-/sexstegsflöden.
- Lägger till ett sammanhängande regressionstest för ny cup → foto/PDF eller manuell start → planer/tider → schema → manuell korrigering → kontroll → publicering.
- Bevarar skyddet mot tyst överskrivning av befintliga/importerade scheman.
- Ingen produktfunktion tas bort i denna release; fokus är att göra den nya nybörjarresan verifierbar inför push.
