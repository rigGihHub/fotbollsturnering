# v366 – Preview-first schedule optimizer

- Nytt verktyg: **Optimera befintligt schema** under schemaverktygen.
- CupNavi räknar först fram ett förslag utan databasändringar.
- Före/efter visar korta vilor, långa håltider, spridning i lagens kortaste vila och kortaste faktiska vila.
- Optimeringen flyttar endast befintliga tid/plan/domar-slots mellan ospelade, olåsta gruppmatcher.
- Planutnyttjande, planernas tidsfönster och domarnas befintliga tidsluckor bevaras eftersom själva slotsen inte flyttas.
- Lag med godkända schemaönskemål eller sen-startpreferenser skyddas från automatisk flytt.
- Förslag som introducerar lagöverlapp accepteras aldrig.
- Ingen ändring sparas förrän arrangören väljer **Använd det förbättrade schemat**.
- Vid tillämpning körs befintlig färgmedveten hemma/borta-balans för ospelade gruppmatcher.
- Publicerad status nollställs när ett optimerat schema tillämpas så att det måste kontrolleras/publiceras på nytt.
