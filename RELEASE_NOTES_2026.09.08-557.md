# CupNavi v557 – Photo Schedule Persistence

- Synkroniserade plantider är fortsatt standard för nya cuper; fallback-migrationens default är nu också synkad till `1`.
- Planadresser blockerar bara flödet när arrangören uttryckligen har aktiverat restids-/adressplanering.
- Pausfältet heter **Paus mellan halvlekar/perioder** och visas bara vid minst 2 halvlekar/perioder.
- Ett granskat matchprogram från foto/PDF är nu förvalt att följa med när cupen skapas.
- Smart bildimport återanvänder samma redan uppladdade bild för strukturerad schemaextraktion och skickar resultatet vidare till Schema-sidan. Ingen andra uppladdning behövs.
- Schema-sidan visar direkt det förberedda matchprogrammet för granskning. Manuell omläsning finns bara kvar som recovery för äldre importer.
- Importerade matcher sparas låsta och behandlas som befintligt schema; de ändras bara via explicit manuell redigering/reparation.
