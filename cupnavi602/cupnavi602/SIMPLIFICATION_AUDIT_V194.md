# CupNavi v.1.194 – Förenklings- och rensningsaudit

## Metod
Audit av senaste v.1.193-koden: huvudnavigation, 22 Admin-sidor, publik vy, formulär, filter, status/feedback, teknisk struktur, CSS-lager, state och databasflöden. Inga osäkra funktioner raderas permanent.

## Inventering – omfattning
- 22 Admin-sidor.
- 5 övergripande Admin-områden.
- 49 explicita `st.button`-anrop, 43 `st.selectbox`, 37 expanders och 28 formulär i huvudfilen.
- 20 separata `<style>`-block från flera designgenerationer.
- 235 funktionsdefinitioner i `app.py` före rensning.
- Två faktiska definitioner av `_set_view_mode` och två av `render_empty_state` hittades.

## Rensningsrapport

| Område | Nuvarande problem | Rekommendation | Åtgärd | Risk | Prioritet |
|---|---|---|---|---|---|
| Visningsläge | `_set_view_mode()` definieras två gånger; senare version skriver över direct-link-logik | Ha en enda sanningskälla | **TA BORT** duplicerad definition | Låg, testbar | P0 |
| Empty state | Två implementationer; den första är död efter senare definition | Behåll den semantiska/a11y-versionen | **TA BORT** verifierad död implementation | Låg | P1 |
| Admin-navigation | Många situationsbundna verktyg syns samtidigt inom varje område | Visa kärnsidor direkt, övriga under Fler verktyg | **VISA VID BEHOV** | Låg | P1 |
| Admin-flöde | Rekommenderad CTA + föregående/nästa + gruppnav ger tre parallella vägar | Låt rekommenderad CTA dominera; gruppnav räcker för fri navigering | **FÖRENKLA** | Låg | P1 |
| Sidebar | Databasbackend visas för vanliga administratörer | Flytta teknisk driftinfo från normal UX | **TA BORT** från normal presentation | Låg | P1 |
| Följ mitt lag | Självklar förklaring visas även innan val | Låt label/help bära instruktionen | **FÖRENKLA** | Låg | P2 |
| Kommunikation | Sponsorer och Erbjudanden är redan nästan samma arbetsområde | Behåll sammanslagen navetikett "Partners & erbjudanden" | **SLÅ IHOP** på navigationsnivå, redan genomfört | Låg | P1 |
| Statistik | Tabeller och Skytteligor delar informationsbehov | Behåll "Tabell & statistik" som nav-ingång | **SLÅ IHOP** på navigationsnivå, redan genomfört | Låg | P1 |
| Kontroller / Problem & lösningar | Närliggande diagnostiska behov, men olika intern logik | Visa som sekundära verktyg tills användningsdata finns | **VISA VID BEHOV / UTRED** | Medel | P2 |
| Instruktioner | Steg-för-steg-hjälp konkurrerar med kontextuell vägledning | Behåll men flytta under Fler verktyg | **FLYTTA** | Låg | P1 |
| Trupper / Import | Behövs bara i vissa cupupplägg | Behåll under Fler verktyg i Deltagare | **VISA VID BEHOV** | Låg | P1 |
| Funktionärer / Cupverktyg | Viktiga men situationsbundna | Behåll under Fler verktyg i Organisation | **VISA VID BEHOV** | Låg | P1 |
| Besöksstatistik | Sekundär drift/analys, inte kärnflöde | Behåll under Fler verktyg | **VISA VID BEHOV** | Låg | P1 |
| CSS | 20 stilblock från flera generationer; hög override-komplexitet | Konsolidera successivt efter visuell regressionstestning | **UTRED** – inte säkert att radera i detta steg | Hög | P2 |
| `app.py` storlek | Monolitisk fil >16k rader skapar förändringsrisk | Bryt ut UI-komponenter gradvis, en domän i taget | **UTRED** – ingen big-bang-refaktor | Hög | P2 |
| Statusmeddelanden | Stor mängd info/warning/success-kopior kan skapa brus | Mät vilka som är dubblerade innan borttagning | **UTRED** | Medel | P2 |
| Avancerade sportflöden | Kan se sällan använda ut men är produktspecifika | Behåll tills faktisk användning/produktbeslut finns | **BEHÅLL / UTRED** | Hög | P3 |
| Säkerhet/backup/historik | Sällan använda men kritiska | Förenkla endast presentation, aldrig ta bort | **BEHÅLL** | Kritisk | P0 |

## Funktionsklassificering
### Kärnfunktioner – BEHÅLL
Adminöversikt, Lag, Grupper, Schema, Matcher & resultat, Tabell/statistik, Slutspel, Turneringsvy, Matchrapportör, publicering, resultat, lifecycle-skydd.

### Stödfunktioner – BEHÅLL men sekundära
Cupinställningar, Domare, Önskemålscentral, Matchhändelser, Partners/erbjudanden, Besöksstatistik.

### Avancerade – VISA VID BEHOV
Trupper, Import, Funktionärer, Cupverktyg, Kontroller, Problem & lösningar, Instruktioner.

### Brus / verifierat tekniskt överskott
Duplicerad `_set_view_mode`, första döda `render_empty_state`, normal användartext om databasbackend, redundanta föregående/nästa-knappar bredvid rekommenderad CTA.

## Medvetet inte borttaget
Backup/restore, historik, papperskorg, audit/error-loggning, livscykelskydd, behörigheter, rate limiting, säkerhetsflöden, multisportkod och avancerade sportspecifika funktioner. Dessa kan vara sällan synliga men fyller kritiska eller framtida produktbehov.
