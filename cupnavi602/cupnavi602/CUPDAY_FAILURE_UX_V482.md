# CupNavi v482 — Cupday Failure UX

v481 gjorde Turso-fel säkra på databasnivå. v482 gör dem begripliga för människan vid planen.

Vid ett oväntat skrivfel får rapportören nu ett tydligt besked:
- CupNavi kan inte bekräfta om ändringen sparades,
- tryck inte igen direkt,
- ladda om matchen och kontrollera serverläget,
- om ändringen redan syns ska den inte registreras igen.

Skyddet används i snabbresultat, matchstatus, mål + målskytt, undo av mål, spelarhändelser, massinmatning och bulkresultat.

Ingen schemaändring. Schema v32.
