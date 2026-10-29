@echo off
cd /d "%~dp0"
if /I "%~1"=="--demo" goto demo
".venv\Scripts\python.exe" -m backend --open --port 8765
if errorlevel 1 pause
exit /b
:demo
echo Open http://127.0.0.1:8766/fixture/connect - synthetic demo, no model calls.
".venv\Scripts\python.exe" -m tools.ui_fixture --port 8766
if errorlevel 1 pause
