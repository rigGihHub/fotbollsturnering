# CupNavi Web – v613 migration foundation

Detta är första fristående Next.js-frontenden för CupNavi. Den ersätter **inte** Streamlit ännu.

## Mål

- Publikvyn migreras först.
- Python/FastAPI/Turso behålls som datalager och domänlogik.
- CupNavi får ett eget UI utan Streamlits layoutbegränsningar.
- Streamlit fortsätter fungera parallellt under migrationen.

## Lokal start senare

1. Starta API: `uvicorn cupnavi_api.main:app --reload --port 8000`
2. `cd frontend-next`
3. `npm install`
4. `npm run dev`
5. Öppna `/cup/<public_slug>`.

Miljövariabel vid separat API-host: `CUPNAVI_API_BASE` eller `NEXT_PUBLIC_CUPNAVI_API_BASE`.

## Designprincip

**Editorial daylight × football collectibles × Text-TV 330 × future matchday system**.

Mörka ytor reserveras för live/resultat/statistik. Övriga ytor är ljusa med mycket hög textkontrast.
