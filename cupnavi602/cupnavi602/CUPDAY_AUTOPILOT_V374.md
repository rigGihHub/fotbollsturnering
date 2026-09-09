# v374 – CupNavi Autopilot

- Cupdagen har fått en första konservativ Autopilot.
- Autopilot använder explicit Pågår/Paus-status och faktisk starttid för att uppskatta verklig planförsening.
- En gammal schematid skapar aldrig ensam en falsk försening.
- Systemet räknar hur många kommande matcher på en försenad plan som riskerar att påverkas.
- Autopilot upptäcker också när en pågående matchs verkliga förskjutning riskerar att ge samma lag för kort vila före nästa match.
- Förslag är preview-first: Autopilot ändrar aldrig schemat själv.
- Förseningsförslag kan skickas direkt till befintligt verktyg Automatisk matchförsening, med plan och minuter förifyllda.
- Arrangören granskar fortfarande exakt vilka matcher som flyttas innan Tillämpa förseningen används.
- Ingen schemaändring; databasschema kvar på v30.
