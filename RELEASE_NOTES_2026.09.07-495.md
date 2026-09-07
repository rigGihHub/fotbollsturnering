# CupNavi v495 – PUBLIC UX + PDF II

- Fixar PDF-hämtningen för Streamlits deferred download-worker: PDF-snapshoten använder nu en egen läsanslutning och är inte beroende av `st.session_state` i bakgrundstråden.
- PDF-validering kräver nu komplett PDF-signatur, rimlig storlek och EOF-markör innan filen skickas.
- Cupklockan har fått en tydligare CupNavi/Text-TV-inspirerad livepanel med bättre kontrast och tabulära siffror.
- Delning ligger över tillgänglighetskontrollen i vänsterflanken. Tillgänglighet är mindre och visuellt nedtonad.
- Publik huvudnavigation tillåter radbrytning och klipper inte längre etiketter med ellips.
- Cupinfo använder konsekventa kort/rutor för cupområde, praktisk information och övriga informationsblock.
- Vägbeskrivning är integrerad i respektive platskort.
- Ingen ändring av resultat-, schema-, slutspels- eller skrivsäkerhetslogik.
