@echo off
setlocal
cd /d "%~dp0.."
set "PYTHONPATH=%CD%\src;%PYTHONPATH%"
python scripts\predixai_support_resistance_zones.py %*
