@echo off
setlocal
cd /d "%~dp0.."
set "PYTHONPATH=%CD%\src;%PYTHONPATH%"
python scripts\predixai_trader_db_status.py %*
