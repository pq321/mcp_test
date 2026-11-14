@echo off
chcp 65001 >nul
cd /d "%~dp0"
if exist "PoliticsMemory-Sync.exe" (
  "PoliticsMemory-Sync.exe"
) else (
  where py >nul 2>nul
  if not errorlevel 1 (py -3 progress_server.py) else (python progress_server.py)
)
pause
