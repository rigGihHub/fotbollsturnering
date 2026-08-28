# CupNavi v1.259 – Performance round 2 + AI roster import

## Mål

1. Minska onödiga databasvarv och tung kod vid vanliga knapptryckningar/navigationer.
2. Låta admin dra in foto/skärmdump av en tidigare laglista och AI-assisterat registrera spelarna i valt lag.

## Prestanda

- Global admin-sökning använder nu ett enda CTE/UNION-anrop i stället för tre till fyra sekventiella databasfrågor per sökning.
- Matchtruppsverktyget på Trupper laddas lazy via toggle. Tidigare körde Streamlit innehållet i den kollapsade expandern och hämtade samtliga schemalagda matcher vid varje rerun.
- Konsekvensanalys under Cupinställningar laddas först när administratören öppnar verktyget.
- Fördjupade kontroller laddas först på begäran.
- Teknisk hälsa/backup laddas först på begäran; databashälsokontroll körs inte längre bara för att sidan renderas.
- Matchfrågan för matchtrupp är nu direkt filtrerad på valt lag i SQL i stället för att hämta alla cupmatcher och filtrera i Python.

Ingen långlivad datacache infördes. Freshness/concurrency-skydd lämnas intakta.

## AI-import av spelare

På Admin → Trupper finns **AI-import från foto eller skärmdump**.

Flöde:

1. Välj lag.
2. Dra in en eller flera PNG/JPG/JPEG/WEBP-bilder.
3. Klicka **Läs av med AI**.
4. CupNavi extraherar namn, eventuellt tröjnummer, födelseår och position.
5. Administratören granskar och kan redigera resultatet i en tabell.
6. Redan registrerade namn avmarkeras automatiskt.
7. Först när admin klickar Importera skrivs spelarna till databasen, i en batch.

AI:n instrueras att inte gissa saknade nummer, födelseår eller position. Allt ska granskas innan lagring.

### Konfiguration

Funktionen är server-side och kräver `OPENAI_API_KEY` i Streamlit Secrets eller miljövariabel. Modellen kan bytas med `CUPNAVI_AI_ROSTER_MODEL`; default är `gpt-5.6-luna` för låg kostnad/latens.

Bilder komprimeras/nedskalas före API-anrop när Pillow finns tillgängligt för att minska uppladdningstid och visionkostnad.

## Ingen schemaändring

v1.259 kräver ingen databasmigrering.
