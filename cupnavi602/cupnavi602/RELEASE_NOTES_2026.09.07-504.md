# CupNavi 2026.09.07-504-SCHEDULE-PRESERVATION-NAV

- Fixar admin-CTA:n så navigering till Schema inte hoppar tillbaka till föregående vy.
- Om ett schema redan finns visas nu granska schemaändring i stället för automatisk regenerering.
- Befintligt schema ändras inte automatiskt; uttrycklig bekräftelse krävs innan ett ospelat schema skapas om.
- Spelade matcher lämnas oförändrade.

Viktigt om dokumentimport: dokumenttolkningen hittar och visar matchprogram som granskningsförslag. I denna release skrivs dokumentets matchprogram inte automatiskt in i matchtabellen; lag och grupper kan importeras. Därför kan en importerad PDF/bild fortfarande visa 0 matcher tills ett schema faktiskt har lagts in eller genererats.
