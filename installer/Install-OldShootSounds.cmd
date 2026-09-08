@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install-OldShootSounds.ps1" %*
if errorlevel 1 pause
