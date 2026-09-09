# CupNavi v462 — Public First-Screen Audit

## Fokus
Förälder/spelare ska på första mobilskärmen förstå:
1. Nästa match
2. Senaste resultat
3. Vad jag kan göra härnäst

## Förändrat
- Nästa match ligger kvar i Mitt lag-hero.
- Senaste resultat flyttas direkt under hero-kortet.
- Primär match-CTA ligger direkt efter senaste resultatet.
- Vägbeskrivning ligger bakom en kompakt expander.
- Kommande matcher visar tre först.
- Resterande kommande matcher ligger bakom `Visa alla X kommande matcher`.
- Ingen extra DB-fråga för senaste resultat eller kommande matcher.

## Säkerhet
Ingen resultatlogik, auth, schema, DB-writer eller notifieringslogik ändras.
Schema v32.
