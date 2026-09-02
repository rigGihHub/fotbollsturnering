# v361 – Cupdagen kontrollcentral

- Ny mobil först-sida: Cupdagen, under Matcher.
- Visar matcher som spelas nu, startar inom 45 minuter, resultat som borde vara rapporterade och dagens färdigrapporterade matcher.
- Planstatus visar aktuell match, nästa match och om äldre resultat saknas på respektive plan.
- Direktknappar leder till Resultat, Försening/Cupverktyg och Schema.
- Cupdagen använder den befintliga inbyggda klockan i sidopanelen och gör inga automatiska databaswrites.
- Statusberäkningen är deterministisk och tar hänsyn till matchlängd samt 10 min rapporteringsmarginal.
- Sidan är operativ och separat från förberedelseflödet; den ändrar inte schemamotorn.
