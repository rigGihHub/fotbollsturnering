# CupNavi v458 — Interaction Latency Audit

## Mål
Minska dubbelkörningar efter klick utan att röra transaktions-, samtidighets- eller resultatsäkerhet.

## Audit
- Inventerade 102 explicita `st.rerun()` i `app.py`.
- Klassificerade resultat-, schema-, auth- och samtidighetsreruns som säkerhets-/freshness-kritiska och lämnade dem orörda.
- Identifierade rena navigationsinteraktioner där Streamlit redan gör en normal rerun efter widgethändelsen.

## Förbättrat
- Språkbyte använder `on_change` och går från normal rerun + explicit rerun till en enda körning.
- Adminstartens val `Skapa ny cup` / `Administrera befintlig cup` använder callbacks.
- Tillbaka-knappar i adminstart använder callbacks.
- `Öppna cup` sätter hela routing-state i callback före den normala rerunnen.
- Generering/regenerering av rapportörs-/domarkod visar den nya koden i samma renderpass och behöver inte en extra full rerun.
- Explicita reruns i `app.py` minskar från 102 till 94.

## Medvetet inte ändrat
- Resultat, livehändelser, schemaändringar, konfliktåterhämtning och autentisering behåller sina explicita reruns där färsk serverdata eller state-reset krävs.
- Ingen DB-logik, poänglogik eller schemaalgoritm ändrad.
- Schema v32.

## Förväntad effekt
Mindre upplevd väntetid i låg-risk men frekventa navigationsflöden, framför allt adminstart och språkbyte. Cupdagskritiska skrivningar behåller samma säkerhetsnivå.
