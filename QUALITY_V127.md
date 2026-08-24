# QUALITY V127

Version: 2026.08.24-127-SHARE-PERFORMANCE-UX

- Dela cupen körs i ett Streamlit-fragment för att undvika full rerun av Turneringsvyn.
- Delningspanelen har ett eget ljust designsystem för länkar, knappar och URL-yta.
- QR-generering sker endast när delningspanelen är öppen.
- Publikstatistiken slår ihop spelade och totala matcher till `X av Y`.
- Regressionstester täcker fragment, lazy QR, ljus share-UI och sammanslagen matchstatus.
