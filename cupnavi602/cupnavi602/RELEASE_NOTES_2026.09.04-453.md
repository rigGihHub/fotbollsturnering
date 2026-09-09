# CupNavi 2026.09.04-453-NETWORK-DOUBLE-TAP-SAFETY

## Varför
Inför skarp cup behöver rapportören kunna förstå vad som verkligen nått servern vid segt nät, och ett upprepat/stale tryck får inte skapa en extra måländring.

## Ändrat
- Tydligare serverkvitto efter live-mål: **Mål säkert sparat på servern**.
- Stale/samtidiga måltryck förklarar uttryckligen att ingen extra måländring sparades.
- Hjälptext vid live-mål säger att rapportören ska vänta på grön bekräftelse i stället för att dubbeltrycka vid segt nät.
- Offlineutkast visar browserns Online/Offline-status.
- Offlineutkast autosparar lokalt när hemma- eller bortasiffran ändras.
- Offlineutkast förklarar uttryckligen att lokal data inte synkas automatiskt.
- Nätgenrep med flygplansläge, återanslutning, reload och två telefoner dokumenterat.

## Säkerhetsmodell
Live-mål använder fortsatt en transaktion med optimistiskt lås på både matchresultat och spelarstatistik. Ett stale andra försök kan därför inte tyst skriva över den första serverversionen.

## Schema
Ingen schemaändring. Fortsatt schema v32.
