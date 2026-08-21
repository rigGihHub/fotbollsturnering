# CupNavi 2026.08.21-86-SPONSOR-HOTFIX

Sponsorfliken:
- Sponsorernas webbplatsvalidering använder inte längre `re.match`.
- Webbplatsadresser valideras med `urllib.parse.urlparse`.
- `example.se` accepteras och normaliseras automatiskt till `https://example.se`.
- Samma validering används både när sponsor skapas och redigeras.
- Regressionstest säkerställer att sponsorfliken inte längre är beroende av regex för URL-validering.
