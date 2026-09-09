# CupNavi v563 – Invitation Links

## Varför
v561 kunde skapa lokala administratörer direkt med ett tillfälligt lösenord. Det fungerar som reservväg, men kräver att cupägaren delar ett lösenord manuellt.

## Nytt
- Åtkomstcenter har nu **Bjud in lokal administratör** som rekommenderad väg.
- Cupägaren skapar en personlig, tidsbegränsad inbjudningslänk för namn + e-post.
- Endast en SHA-256-hash av token lagras i databasen; själva länktoken visas efter skapandet och kan inte återskapas från databasen.
- Inbjudan gäller 3, 7 eller 14 dagar.
- Ny länk till samma cup + e-post återkallar äldre väntande länkar.
- Väntande inbjudningar visas i Åtkomstcenter och kan återkallas.
- `?invite=` öppnar Admin/onboarding direkt från huvuddomänen.
- Befintlig användare loggar in och accepterar.
- Ny användare skapar profil, väljer eget lösenord och kopplas automatiskt till just den inbjudna cupen.
- Inbjudan är bunden till e-postadressen och kan inte accepteras från ett annat konto.
- Ägarrollen kan inte skrivas över; inbjudan ger rollen `admin`.
- Direkt skapande med tillfälligt lösenord finns kvar som reservväg.

## Säkerhet
- Token lagras inte i klartext.
- Utgångstid, accepterad-status och återkallad-status kontrolleras server-side.
- Medlemskapet skapas först efter verifierad inloggning/profil med exakt inbjuden e-postadress.
