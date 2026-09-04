# CupNavi v446 – Min cup: nästa match som direktåtgärd

## Varför
"Mitt lag" visade redan nästa match tydligt, men användaren behövde gå via hela lagets matchlista för att öppna just den matchen. På cupdagen ska nästa relevanta handling vara självklar och snabb på mobilen.

## Ändring
- Lägger en tydlig primär knapp **"⚽ Öppna nästa match"** direkt under den befintliga nästa-match-kortytan.
- Knappen öppnar exakt nästa match med `?match=<id>` och behåller valt lag i länken.
- Ingen ny faktaruta dupliceras; tid, motståndare och plan fortsätter ägas av den befintliga hero-vyn.
- Ingen extra DB-fråga introduceras: match-id tas från den redan byggda `favorite_snapshot`.
- Navigeringen använder callback och en normal Streamlit-rerun, utan explicit extra rerun.

## Effekt
Färre tryck från "Mitt lag" till den match användaren sannolikt vill öppna härnäst, utan att försämra första laddningens prestanda.
