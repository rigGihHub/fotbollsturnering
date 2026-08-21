# CupNavi 2026.08.21-79-ANALYTICS

Ny adminfunktion: Besöksstatistik.

Mäter endast den publika turneringsvyn:
- unika besökssessioner
- sidvisningar
- dagens besök och sidvisningar
- aktiva sessioner senaste 30 minuterna
- genomsnittliga sidvisningar per session
- utveckling per dag
- enhetstyp (mobil/dator/surfplatta)
- webbläsare
- trafikkälla
- 50 senaste besökssessionerna

Periodfilter: 7, 30, 90 dagar eller all tid.

Integritet:
- ingen IP-adress lagras
- sessionsnyckeln är slumpmässig
- sidvisningar räknas högst en gång per minut per session/cup för att Streamlits reruns inte ska blåsa upp statistiken

Databasschema: v4.
