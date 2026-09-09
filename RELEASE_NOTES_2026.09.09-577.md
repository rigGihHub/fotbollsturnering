# CupNavi v577 – Initial Import Carries Groups

- Den första foto-/dokumentimporten är nu ett återanvändbart setup-underlag, inte en engångstolkning.
- Hittad gruppindelning sparas per cup och visas igen på Steg 3 · Grupper.
- Importerade lag kan läggas in direkt medan gruppplaceringen normalt väntar till Grupp-steget för granskning.
- Om ett komplett importerat matchschema väljs följer grupperna med direkt eftersom schemat behöver dem strukturellt.
- Steg 3 får en egen väg: `📦 Från första importen`, så samma foto behöver inte laddas upp eller analyseras igen.
- Befintliga grupper skrivs aldrig över automatiskt.
- Databasschema v35: `tournament_setup_imports` lagrar det granskade setup-underlaget robust över senare sessioner.
