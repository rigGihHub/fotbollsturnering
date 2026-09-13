# CupNavi Next admin – feature parity audit

Status: 2026-09-13

Syfte: innan större nyutveckling ska den nya Next-adminen jämföras mot den äldre Streamlit-adminen och `cupnavi_core`. Funktioner som redan byggts och fortfarande skapar värde ska återföras i stället för att byggas om från minnet.

## Bekräftat återställt

- Ny cup som opublicerat utkast.
- Ägarflöde för ta bort cup, papperskorg, återställ och töm papperskorg.
- Foto/PDF/TXT-import i Ny cup.
- Flera filer i samma AI-avläsning.
- Review-first: inget skapas innan användaren granskat avläsningen.
- Cupnamn och datum från underlaget.
- Lag från underlaget.
- Grupper och gruppkopplingar från underlaget.
- Plan-/anläggningsnamn från underlaget.
- Strukturerade gruppspelsregler när de uttryckligen hittats.
- Importvarningar visas innan cupen skapas.

## Bekräftat i legacy men ännu inte fullt migrerat till Next

- Importerat matchschema/fixtures från första underlaget.
- Importerat slutspel och deltagarkällor.
- Persistens av första importens snapshot så att samma foto/PDF inte behöver läsas in igen i senare setupsteg.
- Separat senare fotoimport av gruppindelning med strikt matchning mot redan registrerade lag.
- Revisionsimport: jämföra ett nytt/reviderat underlag med befintlig cup.
- Matchnivågranskning av ändrat/oförändrat/nytt/borttaget innan revision appliceras.
- Konsekvenskontroll av revisioner mot plan-, lag- och domarkrockar samt vilotid.
- Reparationsförslag för konflikter i reviderade scheman.
- Import av planernas uttryckliga öppettider/tidsfönster.
- Import av särskilda slutspelsregler/matchtider.
- Foto-/dokumentbaserade matchställ samt senare verifieringsflöden.

## Next-moduler som måste jämföras mot legacy innan de kallas kompletta

1. Cupinfo
2. Lag
3. Grupper
4. Planer & tider
5. Regler
6. Schema
7. Domare
8. Slutspel
9. Publicering
10. Matchrapportering
11. Import/revisionsimport
12. PDF & export
13. Behörigheter/inbjudningar
14. Publik cup / matchdag / Text-TV

## Migreringsregel

- Ingen legacy-funktion ska återföras blint bara för att den finns.
- Funktioner ska först bedömas mot dagens produktflöde och mobil-UX.
- Import får aldrig tyst skriva över befintlig cupdata.
- Osäkra AI-tolkningar ska visas som varningar eller förslag, inte behandlas som fakta.
- Schema, spelade matcher och publicerad data kräver särskilt starka skydd mot destruktiva ändringar.

## Nästa block

1. Persisted import snapshot i Next.
2. Import av verkligt matchschema efter granskningssteg.
3. Slutspelsimport med källor och validering.
4. Full genomgång av legacy-testkontrakt v572–v612 mot dagens Next-gränssnitt.
