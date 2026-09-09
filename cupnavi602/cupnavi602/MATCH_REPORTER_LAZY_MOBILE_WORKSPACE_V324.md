# CupNavi v324 – Match Reporter lazy mobile workspace

## Problem
Matchrapportören använde `st.tabs` för CupNavi Score, Matchhändelser, Domarcentral och Offlineutkast. Streamlit exekverar innehållet i alla tabs på varje rerun, även när bara en tab är synlig. Det gav onödiga repository-anrop, DataFrame-byggen och UI-arbete i ett mobilkritiskt liveflöde.

## Ändring
- Ersätter `st.tabs` med en native `st.segmented_control`.
- Endast vald arbetsyta exekveras.
- CupNavi Score är fortsatt standardvy.
- Resultat-, event-, domar- och offlinefunktionalitet är oförändrad.
- Persistence, optimistic locking och concurrency callbacks är oförändrade.

## Effekt
Ett normalt resultatklick behöver inte längre samtidigt bygga Matchhändelser, Domarcentral och Offlineutkast. Det minskar arbete per rerun och gör arbetsytan tydligare på mobil.
