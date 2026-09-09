# CupNavi v1.266 – Mobile public performance & UX

- Döljer Streamlit Cloud-toolbar/deploy-chrome (bl.a. "Fork") utan att ta bort headern som admin behöver för sidomenyn.
- Flyttar mobilens cupnavigation från fast bottenbar till sticky navigation i överkant.
- Samordnar responsiva breakpoints till 900 px så summary-metrics inte kan pressas till extremt smala kolumner på Android/tablet-viewports.
- Säkrar min-width, wrapping och grid-layout för metrics och live-highlights.
- Behåller 1-kolumns highlights på riktigt smala telefoner för läsbarhet.
- Streamlit client toolbarMode sätts till minimal för mindre hosting-chrome och något lättare mobilrendering.
