# CupNavi v1.274 – Public shell decomposition

## Mål
Fortsätta den stegvisa nedbrytningen av `app.py` utan att ändra publik funktionalitet eller datamodell.

## Ändrat
- Ny modul `cupnavi_core/public_shell_view.py`.
- Informationsskärmens presentation, 30-sekunders auto-refresh, live/kommande/senaste-matchkort, grupptabeller och sponsorlistning har flyttats ur `app.py`.
- Publik cup-hero byggs nu av den rena hjälpfunktionen `build_public_hero_html`.
- Domän- och databasfunktioner injiceras fortsatt från `app.py`; inga persistence-regler har flyttats eller ändrats.

## Riskkontroll
- Ingen migration.
- Ingen ny dependency.
- Ingen förändring i query-parametrar, informationsskärmens refresh-intervall eller antal matcher/tabeller som visas.
- Matchrapportering, admin, concurrency-skydd och publiceringslogik är orörda.

## Verifiering
Riktade regressionstester verifierar hero-status/escaping, informationsskärmens urval och att `app.py` använder den nya modulgränsen. Full browser-/enhets-E2E anges separat och får inte påstås passerad om den inte körts.
