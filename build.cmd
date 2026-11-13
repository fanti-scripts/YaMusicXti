@echo off
setlocal
cd /d "%~dp0"

set "PY="
if exist "installer\python\python.exe" set "PY=installer\python\python.exe"
if not defined PY (
  where python >nul 2>nul
  if not errorlevel 1 set "PY=python"
)
if not defined PY (
  echo Python not found. Keep installer\python or install Python 3.
  exit /b 1
)

"%PY%" tools\build.py
exit /b %errorlevel%
