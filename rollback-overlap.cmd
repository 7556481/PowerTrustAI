@echo off
cd /d "%~dp0"
".venv\Scripts\python.exe" -m tools.managed_overlap --rollback --open %*
if errorlevel 1 pause
