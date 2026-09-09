# CupNavi v329 – Mobile Admin Home

Version: `2026.08.30-331-MOBILE-MATCH-EVENT-ENTRY`

## Mål
Göra CupNavis fem viktigaste adminarbetsytor direkt åtkomliga i huvudflödet på mobil utan beroende av sidebar eller djup gruppnavigation.

## Förändringar
- Ny synlig sektion `📱 Snabbadmin` högst i Adminöversikten.
- Fullbreddsgenvägar till Lag, Grupper, Schema, Resultat och Publicera.
- Genvägarna använder befintlig `_set_admin_page` och samma sidor/skrivvägar som desktop.
- Schema och Publicera leder båda till den befintliga samlade arbetsytan `Skapa och publicera schema`; ingen parallell publiceringslogik introduceras.
- Rekommenderat nästa steg markeras som primärt när det matchar en snabbadmin-genväg.
- Avancerad navigation, sök, sidebar och tidigare snabbvägar finns kvar.

## Säkerhet och dataintegritet
Releaseändringen innehåller inga nya databaswrites, inga authförändringar och inga ändringar i match-/schema-/publiceringspersistens.
