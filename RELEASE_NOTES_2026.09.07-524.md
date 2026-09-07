# CupNavi v524 — Primary flow pitch count fix

- Fixar ett produktionsfel där Lag, Grupper och Schema kunde krascha med `KeyError: pitches_n`.
- Den gemensamma snapshoten för huvudflödet hämtar nu även antal planer innan nybörjarguiden använder värdet.
- Navigeringen till `Planer & tider` när plan saknas är oförändrad men fungerar nu på alla huvudsteg.
- Lägger till regressionstest som säkerställer att `pitches_n` finns i den primära flödesfrågan.
