@echo off
chcp 65001 >nul
cd /d "%~dp0"
if exist "PoliticsMemory-Sync.exe" --select-drive-folder (
  "PoliticsMemory-Sync.exe" --select-drive-folder
) else (
  where py >nul 2>nul
  if not errorlevel 1 (py -3 progress_server.py --select-drive-folder) else (python progress_server.py --select-drive-folder)
)
pause
