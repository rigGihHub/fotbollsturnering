# CupNavi Quality V124

Version: 2026.08.24-124-COMPETITION-CLASSES

- Syntaxkontroll: godkänd
- Full pytest: 286 tester godkända
- Databasschema: v14
- Tävlingsklasser är nu riktiga databasobjekt i `competition_classes`
- Lag och grupper kopplas till tävlingsklass via `competition_class_id`
- Befintliga åldersklassdata migreras/backfillas och textfälten behålls tills vidare för bakåtkompatibilitet
- En fysisk cup hanteras som en turnering med flera sportsligt separata tävlingsklasser
- Ny cup och duplicerad cup synkar tävlingsklasser automatiskt
- Publik matchfiltrering använder begreppet Tävlingsklass
- Lag- och gruppadministration använder Tävlingsklass och säkrar att lag bara placeras i grupp inom samma klass
