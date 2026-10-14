@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Environnement Python absent. Voir README.md.
  pause
  exit /b 1
)
echo Ouvrir http://127.0.0.1:8765 dans votre navigateur.
echo Garder cette fenetre ouverte. Ctrl+C pour arreter.
".venv\Scripts\python.exe" "src\serve_sessiondna.py"
if errorlevel 1 pause
