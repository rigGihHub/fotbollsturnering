@echo off
setlocal
cd /d "%~dp0"
echo CupNavi - rensar gamla nastlade projektkopior...
python scripts\cleanup_legacy_nested_repos.py --apply
if errorlevel 1 (
  echo.
  echo Rensningen misslyckades. Kontrollera att Python ar installerat och att filerna inte ar lasta.
  pause
  exit /b 1
)
echo.
echo Klart. Oppna GitHub Desktop och kontrollera att gamla filer visas som Deleted.
pause
