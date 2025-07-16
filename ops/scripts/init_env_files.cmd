@echo off
rem Call corresponding ps1 file 
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass ^
    -File "%~dp0init_env_files.ps1" %*
