@echo off
cd /d "%~dp0"
".venv\Scripts\python.exe" -m backend --open --port 8765
if errorlevel 1 pause
