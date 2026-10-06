@echo off
cd /d "%~dp0"
".venv\Scripts\python.exe" -m tools.learning_site serve --open --port 8770
