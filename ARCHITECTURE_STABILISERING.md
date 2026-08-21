# CupNavi – Stabilisering 1.0

## Principer från version 72

1. `app.py` är presentations- och orkestreringslager. Ny komplex affärslogik ska läggas i `cupnavi_core/`.
2. Databasschema ändras genom versionsstyrda migrationer i `cupnavi_core/migrations.py`.
3. En släppt migration får aldrig redigeras. Lägg till en ny version.
4. Produktionsberoenden ligger i `requirements.txt`; test/CI-beroenden ligger i `requirements-dev.txt`.
5. CI måste vara grön innan en version betraktas som releasebar.
6. Kritiska ändringar ska få regressionstest.
7. Turneringar ska kunna säkerhetskopieras innan destruktiva eller större framtida migreringar.
8. Streamlit-specifik state/CSS ska inte flyttas in i kärnmoduler.
9. Nästa arkitektursteg är att bryta ut databasåtkomst och schemamotor från `app.py` stegvis.

## Nya kärnmoduler

- `migrations.py`: schemahistorik och prestandaindex.
- `health.py`: teknisk databasstatus.
- `backup.py`: portabel JSON-backup.
- `config.py`: gemensamma tekniska konstanter.

## Kvarvarande teknisk skuld

`app.py` är fortfarande stor. Det är avsiktligt i denna release: en stor samtidig omskrivning hade ökat regressionsrisken. Nästa fas ska extrahera en domän i taget med testskydd.
