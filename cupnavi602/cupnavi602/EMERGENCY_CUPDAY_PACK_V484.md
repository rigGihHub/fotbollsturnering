# CupNavi v484 — Backup & Emergency Cupday Pack

## Mål
Göra CupNavi robustare när internet eller Turso faller bort under en pågående cup.

## Nytt
- Admin → Kontroll visar ett tydligt **Cupdagens nödpaket**.
- Backupstatus visas direkt i adminsessionen.
- Tidpunkt för senast förberedd backup visas.
- CupNavi påminner om att backupen inte är säkrad förrän JSON-filen faktiskt är nedladdad till en arrangörsenhet.
- Tydlig sexstegsrutin vid avbrott:
  1. tryck inte igen på osäkra writes,
  2. anteckna matchen manuellt,
  3. låt publik cup ligga kvar utan lokal fallback,
  4. läs om serverläget när anslutningen är tillbaka,
  5. registrera bara sådant som saknas,
  6. återställ backup som ny Testmiljö först om större återställning krävs.
- Rekommendation att ha PDF/spelschema sparat på minst en arrangörstelefon.

## Oförändrat
- Backupformatet är portabel JSON med SHA-256.
- Restore skapar alltid ny cup och skriver aldrig över originalet.
- Ingen schemaändring.
- Schema v32.
