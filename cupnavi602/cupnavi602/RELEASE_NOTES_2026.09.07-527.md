# CupNavi v527 — Primary Flow Roundtrip Cut

Performance-only release. Removes one blocking remote schedule-rules/count roundtrip from the common guided setup pages (Cupinfo, Lag, Grupper, Planer & tider) by reusing the existing primary-flow snapshot. Full schedule rules remain lazy and load only on Schema/Kontroll or secondary pages that need them. Adminöversikt now carries referee_mode in its existing aggregate query so no extra fetch is required.
