# v372 – Enkel och avancerad resultatrapportering

- CupNavi Score har nu två tydliga rapporteringslägen: Enkel och Avancerad.
- Enkel är standard och visar bara kärnflödet: välj match, ange resultat, spara och gå vidare till nästa orapporterade match.
- Matchstatus visas kompakt i Enkel när matchen faktiskt Pågår eller är i Paus, men statuskontrollerna tar inte över resultatinmatningen.
- Avancerad visar matchstatuskontroller, mål/assist/kort och specialfall i samma arbetsflöde.
- Straffar, avgörande vinnare och massinmatning ligger i en separat expander i Avancerad och belastar inte standardvyn.
- Oavgjord slutspelsmatch förklarar tydligt att Avancerad rapportering behövs.
- Befintlig separat arbetsyta för Matchhändelser finns kvar för rapportörer som arbetar händelsebaserat.
- Resultatsparande, optimistisk låsning, pushlogik och automatisk matchstatus Slut återanvänder befintliga skrivvägar.
- Ingen schemaändring; databasschema kvar på v30.
