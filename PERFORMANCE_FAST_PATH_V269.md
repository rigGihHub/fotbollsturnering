# CupNavi v1.269 – Public mobile fast path

## Syfte
Fortsätta mobilprestandaarbetet med två lågriskåtgärder som har tydlig kostnad på den publika matchsidan utan att offra färsk data eller concurrency-skydd.

## Ändringar
- Aktivt besökarantal och individuella skytt-/assistledare hämtas nu via en gemensam DB-anslutning på matchsidan.
- Skytt- och assistfrågorna returnerar bara den faktiska ledaren i stället för hela aggregerade spelarlistan. Det minskar payload och Python-sortering på remote libSQL/Turso.
- Väderprognos är nu opt-in på publika matchsidan. Första sidladdningen gör därför inget externt Open-Meteo-anrop om besökaren inte uttryckligen väljer väder.
- Profileraren har fått steget `overview_db_ms` så batchingvinsten går att följa efter deploy.
- Ingen långlivad cache eller integritets-/concurrencylogik har tagits bort.
