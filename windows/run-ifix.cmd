@echo off
rem Double-click launcher for iFix on Windows 11 (runs the GUI inside WSL 2).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run-ifix.ps1" %*
if errorlevel 1 pause
