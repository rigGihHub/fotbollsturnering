# v403 – First cup day handoff

## Varför
Efter publicering gick huvudflödet direkt till den generella resultatvyn även när cupdagen faktiskt pågick. Cupdagen hade dessutom en missvisande statusregel: en match med explicit status `not_started` hamnade som "resultat saknas" så fort planerad avspark passerats, trots att normal matchtid fortfarande pågick.

## Ändringar
- När cupen är publicerad, har ospelade matcher och dagens datum ligger inom cupens start-/slutdatum rekommenderar huvudflödet nu **Cupdagen**.
- Före eller efter cupdatum behålls den vanliga vägen till **Matcher och resultat**.
- Cupdagen skiljer nu på **Starttid passerad** och **Resultat saknas**.
- En `not_started`-match inom beräknad matchtid + rapporteringsmarginal får direktåtgärden **Starta match**.
- Först efter beräknad matchtid + marginal eskaleras den till resultat som saknas.
- KPI:n "Behöver åtgärd" summerar båda typerna och planstatus visar vilken sorts problem som finns.

Ingen extra databasfråga behövs för handoffen; turneringens datum finns redan i den laddade turneringsraden.
