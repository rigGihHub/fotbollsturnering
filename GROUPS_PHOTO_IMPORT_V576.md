# CupNavi v576 – Grupper med fotoimport

Grupper har nu tre tydliga startvägar: CupNavi föreslår, importera från foto eller gör själv.

Fotoimporten kan ta flera PNG/JPG/WEBP-bilder, använder CupNavis befintliga AI-dokumentavläsning och extraherar bara lagnamn + grupp när kopplingen faktiskt framgår. Resultatet visas i en granskningsvy innan något sparas.

Säkerhetsregler:
- inget sparas automatiskt efter AI-avläsning,
- bara registrerade lag som matchar lagnamnet kopplas automatiskt,
- om ett lag i fotot inte kan matchas markeras det för kontroll,
- om cupen redan har grupper används fotoresultatet bara som förslag; befintlig gruppstruktur skrivs aldrig över tyst,
- spelad produktionshistorik förblir låst.
