@echo off
REM Doble clic para abrir la app en tu ordenador (Windows, con Python instalado).
cd /d "%~dp0"
set PY=python
where py >nul 2>nul && set PY=py
echo Instalando lo necesario (solo tarda la primera vez)...
%PY% -m pip install -q -r requirements.txt
echo Abriendo Metrorrey en el navegador...
%PY% main.py
pause
