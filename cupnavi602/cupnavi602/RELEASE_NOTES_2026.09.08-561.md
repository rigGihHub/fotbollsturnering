# CupNavi v561 – Access Center & Local Admins

## Nytt
- Alla koder-sidan fungerar nu som ett samlat åtkomstcenter.
- Cupägare kan skapa eller lägga till lokala cupadministratörer via namn och e-post.
- Befintliga arrangörskonton återanvänds; nya konton får ett säkert tillfälligt lösenord som bara visas direkt efter skapandet.
- Lokala administratörer får endast medlemskap i den aktuella cupen.
- Cupägare kan ta bort lokala administratörers åtkomst utan att ägarrollen kan tas bort av misstag.
- Endast cupägare eller CupNavi driftadmin kan hantera andra administratörer.
- Inloggade arrangörer kan byta sitt eget lösenord från Min profil i åtkomstcentret.
- Koder för lag, matchrapportör och domare ligger kvar på samma sida.

## Säkerhet
- Lösenord lagras fortsatt med scrypt + individuellt salt.
- Tillfälliga lösenord lagras aldrig i klartext och visas bara i skapandeögonblicket.
- Befintlig tenant-isolering via tournament_members behålls.

## Test
- 302 evergreen-tester godkända, 2 avsiktligt deselectade äldre kontrakt.
- 43 aktuella/recenta säkerhets- och funktionskontrakt godkända.
- compileall godkänd.
