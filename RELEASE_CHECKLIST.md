# Releasechecklista CupNavi

1. `python -m py_compile app.py cupnavi_core/*.py`
2. `python -m unittest discover -s tests -v`
3. Kontrollera versionsbadge i appen.
4. Testa Admin-login.
5. Testa lag → grupper → schema → tabeller → matcher → slutspel.
6. Testa demodata och båda testresultat-knapparna.
7. Kontrollera mobil publikvy.
8. Kontrollera att GitHub Actions är grön innan versionen betraktas som godkänd.
