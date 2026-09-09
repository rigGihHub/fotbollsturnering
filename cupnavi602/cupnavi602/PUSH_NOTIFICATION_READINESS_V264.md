# CupNavi v1.264 – Push Notification Readiness

## Mål
Förbereda CupNavi för framtida web push-notiser, särskilt när ett lag som en besökare följer gör mål, utan att aktivera ett halvfärdigt pushflöde i UI:t.

## Implementerat
- Provider-neutral `web_push_subscriptions` för framtida browser/PWA-prenumerationer.
- Durable `push_notification_outbox` med idempotenta event keys.
- Mål-events skapas när ett sparat matchresultat ökar för hemma- eller bortalaget.
- Sänkning/korrigering av resultat skapar aldrig målnotis.
- Hopp med flera mål ger en notifiering för senaste score-state, inte en burst av historiska notiser.
- Eventet skapas i samma DB-transaktion som resultatuppdateringen i samtliga primära resultatflöden.
- Ingen extern pushleverantör, VAPID-nyckel eller service-worker-registrering krävs ännu.

## Framtida aktivering
Nästa steg när push ska slås på är browser/PWA-opt-in, service worker, VAPID-konfiguration och en leveransworker som konsumerar `push_notification_outbox` och skickar endast till aktiva subscriptions med rätt preferenser.

## Integritet
Push-endpoints och browsernycklar exporteras inte i vanliga CupNavi-backuper. En återställd cup kräver ny opt-in från besökaren.
