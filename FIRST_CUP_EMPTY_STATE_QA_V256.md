# CupNavi v1.256 – First-cup empty-state QA

Praktisk QA-runda A startad från tom databas.

## Friktion som hittades
När Admin saknade cuper visades endast "Skapa den första turneringen i vänstermenyn." Det är desktop-specifikt och svagt på mobil, där sidomenyn ligger bakom ☰. Det förklarade inte heller hur liten första skapandeåtgärden faktiskt är.

## Ändring
Tomt Admin-läge använder nu CupNavis befintliga empty-state-komponent och guidar explicit till sidomenyn/☰ samt anger de fyra grunduppgifter som behövs: namn, spelort, sport och cupdag.

Ingen ny funktion eller extra setup har lagts till. Monetization readiness från v1.255 är fortsatt osynlig och inaktiv.
