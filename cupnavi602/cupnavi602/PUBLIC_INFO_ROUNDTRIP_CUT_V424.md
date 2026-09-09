# v424 – Public Info roundtrip cut

Mål: minska väntetiden på den publika Info-sidan utan att dölja eller cacha färsk data.

Ändring:
- reglerna för cupen och matchernas completion-räknare hämtas nu i samma Turso-fråga,
- den separata completion-frågan före Info-renderingen är borttagen,
- befintliga lazy-loads för fullständigt schema, lag, sponsorer och övriga detaljblock är oförändrade.

Effekt: en sekventiell remote DB-roundtrip mindre på standardvägen till publika Info-sidan.
