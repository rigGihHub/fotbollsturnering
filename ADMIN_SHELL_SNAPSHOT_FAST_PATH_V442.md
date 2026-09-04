# CupNavi v442 – Admin shell snapshot fast path

## Mål
Göra vanliga admin-klick och sidbyten snabbare genom att undvika identiska remote DB-anrop i det globala admin-skalet.

## Förändringar
- Primärflödets räknare återanvänds i 5 sekunder mellan snabba reruns.
- Adminöversiktens större kontrollsnapshot återanvänds i 5 sekunder.
- `schedule_rules` + antal schemalagda matcher i sidopubliceringen återanvänds i 6 sekunder.
- Livscykelräknare för publicerad/pågående cup återanvänds i 4 sekunder.
- Alla lokala DB-skrivningar fortsätter att omedelbart tömma admincachen genom befintliga `run()`-invalideringen.
- Utkast fortsätter att helt hoppa över livscykelräkningen.

## Varför det är säkert
TTL:erna är korta och cacheinvalidering sker direkt efter CupNavis egna writes. Externa/live uppdateringar blir därför högst några sekunder gamla i adminskalet, medan vanliga navigeringsklick slipper betala samma Turso-latens om och om igen.

## Ingen domänlogik ändrad
Schema, resultat, publiceringsregler och valideringsregler är oförändrade.
