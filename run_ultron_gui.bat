@echo off
setlocal
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 -m ruller_ai --gui %*
) else (
  python -m ruller_ai --gui %*
)
if errorlevel 1 pause
