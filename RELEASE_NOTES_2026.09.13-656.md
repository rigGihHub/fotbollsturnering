# CupNavi v656 — papperskorg och återställning

- Appägaren kan nu lista cuper som ligger i papperskorgen via admin-API:t.
- En borttagen cup kan återställas till aktiv lista utan dataförlust.
- Återställda cuper kommer tillbaka som opublicerade utkast för att undvika oavsiktlig publicering.
- Vanliga arrangörskonton kan varken läsa papperskorgen eller återställa cuper.
- Regressionstest täcker listning, återställning, behörighet och releasesynk.
