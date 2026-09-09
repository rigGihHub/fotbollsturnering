# CupNavi v434 – Interaction fast path

Fokus: kortare upplevd och faktisk väntetid utan att offra live-känslan.

- Kort session-TTL för den publicerade cupens kärndata (6 s). Snabba flikbyten/filter återanvänder precis hämtat schema och lag i stället för ett nytt Turso-varv.
- Cupinfo-regler + matchstatus återanvänds i 8 s.
- Synliga matchhändelser återanvänds i 5 s.
- Direktlänkens cuphuvud återanvänds i 12 s, vilket tar bort ett remote DB-anrop vid täta fragment/full-reruns.
- Befintlig render/query-cache ligger kvar som första nivå; session-TTL är en andra, kort nivå över reruns.
- Cachefönstren är medvetet korta så live-resultat fortfarande slår igenom inom sekunder.

Målet är framför allt att reducera "CupNavi tänker" vid navigation, filter och upprepade klick där data precis lästs.
