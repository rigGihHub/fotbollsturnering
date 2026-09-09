# CupNavi v1.257 – Public live highlights

## Ändrat
- Publika matchöversikten använder tom yta till höger om grundmetrikerna för kompakta live-highlights.
- Poängledare visas när minst ett lag har spelat gruppspelsmatch. Delade poängledare hanteras utan att dölja oavgjort läge.
- Lag med minst insläppta visas först efter att laget spelat minst en gruppspelsmatch.
- Skytteligaledare visas endast när skytteligan är aktiverad och registrerade mål finns.
- Assistledare visas endast när assistligan är aktiverad och registrerade assist finns.
- Individuella highlights använder samma sorteringslogik som befintliga topplistor och respekterar skyddade spelarnamn.
- Mobilvyn staplar highlights i ett kompakt 2-kolumnsnät.

## Princip
Ingen ny inställning eller administrativ friktion har lagts till. Highlights härleds från redan registrerade cupdata.

## Prestanda
Lag-highlights räknas från den redan laddade publika snapshoten. Matcher-sidan återinför därför inte de gruppqueries som tidigare togs bort i v147. Endast individuell spelarstatistik hämtas, och bara när minst en match är spelad och respektive topplista är aktiverad.
