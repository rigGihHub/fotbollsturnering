# v448 – Mobile playoff live path

## Why
The public playoff was technically responsive, but on a phone it still behaved like a compressed list rather than a cup-day tool. A visitor should understand what is live, what is finished and where the winner goes next without mentally rebuilding the bracket.

## Changes
- Added compact status badges to every mobile playoff match: Kommande, Pågår, Paus or Slut.
- Live and halftime matches get stronger visual focus without affecting desktop bracket rendering.
- Each round now has a compact match count.
- Every mobile match explains the progression path (for example, the winner goes to semifinal/final; final winner takes the gold).
- Final cards receive a dedicated final marker for styling.
- Reuses the already loaded bracket matches and team snapshot; no new database roundtrip was introduced.
- Desktop bracket and bronze-match behavior remain unchanged.

## Performance
The entire mobile enhancement is computed from data already loaded by `render_bracket_tree`. No extra `all_rows()` call exists in the mobile rendering block.
