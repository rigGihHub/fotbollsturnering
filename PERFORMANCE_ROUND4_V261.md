# CupNavi v1.261 – Heavy Admin Performance

Fokus: kortare svarstid vid navigation och knapptryckningar på de tyngsta adminsidorna Schema, Resultat och Trupper.

## Ändringar

- Schema Score/regelkvalitetsanalys är nu verkligt lazy-loaded. Streamlit-expander körde tidigare innehållet även när den var stängd.
- PDF-export och reseinformation på Schema laddas först när användaren aktivt öppnar dem.
- Fem separata matchstatus-COUNT-frågor på Schema har slagits ihop till en enda aggregerad snapshot.
- N+1-frågan för att kontrollera antal lag per grupp är borttagen; gruppstorlek räknas från redan laddade lag.
- Slutspels-specifikationen återanvänds och beräknas inte två gånger på samma render.
- Resultat återanvänder redan laddade matcher för resultatprogress och global sökträff i stället för två extra databasfrågor.
- Den kompletta matchschematabellen på Resultat byggs först när användaren öppnar den.
- Trupper använder O(1)-uppslagskartor för lag- och spelarformattering i widgets i stället för upprepade linjära sökningar.
- Ingen långlivad cache har införts; befintliga concurrency-/freshness-skydd är kvar.
- Releasepaketeringen återställer .github/workflows och .gitignore som saknades i v1.260-ZIP:en men fanns i v1.260-arbetskatalogen.

## Test

- 262 non-E2E-testfiler körda i tre batcher: PASS.
- Python compile/compileall: PASS.
- E2E Python-syntax: PASS.
- Release manifest: genereras före paketering.
