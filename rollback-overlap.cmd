@echo off
cd /d "%~dp0"
D:\PowerTrustAI\.venv\Scripts\python.exe -m tools.managed_overlap --stop %*
if errorlevel 1 exit /b 1
D:\PowerTrustAI\.venv\Scripts\python.exe -m tools.managed_overlap %* --factory component --open
