# CupNavi v583 – Match-level revision approval

## Nytt
- Reviderade PDF-/foto-underlag kan nu granskas match för match.
- Matcher klassas som oförändrade, ändrade, nya eller borttagna.
- Ändrade ospelade matcher kan godkännas individuellt.
- Admin kan välja alla säkra matchändringar i ett klick och därefter avmarkera enstaka.
- Tidändringar behåller befintligt matchdatum och ändrar bara klockslaget.
- Planändringar appliceras endast när det nya plannamnet matchar en befintlig plan exakt.
- Redan startade/spelade matcher är låsta både i UI och genom en ny kontroll inne i skrivtransaktionen.
- Nya matcher läggs inte till automatiskt och borttagna matcher tas inte bort automatiskt; de kräver separat schemagranskning.
- Efter godkända ändringar avpubliceras de berörda matcherna och schemat markeras för ny kontroll.

## Säkerhet
Revisionsflödet är fortsatt review-first. Ingen matchändring sker bara genom att ett dokument analyseras.
