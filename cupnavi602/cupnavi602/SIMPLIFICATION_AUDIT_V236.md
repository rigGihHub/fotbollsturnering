# CupNavi v.1.236 – förenklingsgranskning

## Princip
Förenklingen följer produktkravet att appen ska innehålla så lite som möjligt, men allt
som behövs. Funktionalitet tas inte bort bara för att minska antalet kontroller.

## Genomförd P0/P1-förenkling

| Område | Problem före | Åtgärd | Effekt | Prioritet |
|---|---|---|---|---|
| Skapa cup | Internationella systemval låg mitt i normalflödet | Flyttade Miljö, Språk/region, Tidszon och Landkod till **Fler alternativ** | Färre beslut innan en vanlig cup kan skapas | P0 |
| Skapa cup | Två datumfält visades även för endagscuper | En **Cupdag** är standard; sista dag visas endast när **Cupen pågår flera dagar** är valt | Ett onödigt datumval för normalfallet försvinner | P0 |
| Skapa cup | Flera captions förklarade nästa steg och låsta fält | Tog bort repetitiva instruktioner och behöll information där den behövs | Mindre text att läsa | P1 |
| Testläge | Stor informationsruta visades så snart Testmiljö valdes | Ersatt med kort kontextuell caption i avancerat område | Mindre visuellt brus utan att dölja läget | P1 |

## Klassificering
- **A – måste finnas:** namn, spelort, sport, cupdag, skapa.
- **B – bra att ha:** startmall, flerdagarsval.
- **C – visa vid behov:** testmiljö, språk/region, tidszon, landkod, sista cupdag.
- **D – slå ihop:** första/sista cupdag blir Cupdag + flerdagarsval.
- **E – ta bort:** repetitiva captions som beskrev nästa setupsteg eller upprepade låsning.

## Före/efter
I standardflödet behöver en vanlig endagscup inte längre ta ställning till Miljö,
Språk/region, Tidszon, Landkod eller Sista cupdag. Dessa fem kontroller finns kvar när
de faktiskt behövs. Datamodell, internationell grund och testkontrakt är bevarade.

## Nästa lämpliga förenklingsområde
Adminnavigationen har redan progressiv disclosure från tidigare arbete. Nästa stora
vinst bör därför göras inne på de tyngsta adminsidorna: **Cupinställningar** och
**Skapa och publicera schema**, där sekundära regler bör grupperas efter när de behövs
i stället för att visas samtidigt.
