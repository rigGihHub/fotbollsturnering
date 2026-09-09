# CupNavi v467 — Multi Favorite Timeline

## Syfte
Göra flera favoritlag praktiskt användbara under en cupdag.

## Nytt
- Gemensam kronologisk lista över kommande matcher för alla favoritlag.
- Varje rad visar tid, match, vilket favoritlag det gäller och plan.
- Matcher mellan två favoritlag visas bara en gång och märks med båda lagen.
- Två olika favoritmatcher som startar inom 60 minuter markeras med `⚠`.
- Tidslinjen visar upp till åtta kommande matcher för att hålla mobilvyn kompakt.
- Layouten faller till en kolumn på mycket små telefoner.

## Prestanda
All logik körs på redan laddade `published_matches`.
Ingen extra DB-fråga eller rerun.

## Säkerhet
Ingen resultat-, schema-, auth- eller writerlogik ändras.
Schema v32.
