# CupNavi v465 — Mobile Edge-Case QA

## Fokus
Säkra verkliga telefonproblem som vanlig responsiv CSS ofta missar.

## Förbättrat
- 320 px-navigation använder inte längre 8 px text som nödlösning.
- Små telefoner behåller minst 44–46 px tryckytor.
- Extremt långa lagnamn får brytas inom sin egen kolumn utan horisontell sidscroll.
- Knappar får radbrytas i stället för att skjuta utanför viewporten.
- Landscape med låg viewport-höjd får kompakt men fortsatt användbar sticky navigation.
- Coarse-pointer/touch-enheter får minsta tryckyta även om viewporten klassas som liten surfplatta.
- Safe-area för notch/home-indicator bibehålls.

## Testmatris som koden nu skyddar
- 320 px
- 330 px
- 360 px
- 375/390 px
- 412/430 px
- landscape under 500 px viewport-höjd
- långa lagnamn
- större text/radbrytning
- touch/coarse pointer

## Säkerhet
Endast presentation/CSS och testkontrakt. Ingen DB-, auth-, schema-, resultat- eller writerlogik ändras. Schema v32.
