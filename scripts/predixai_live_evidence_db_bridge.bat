@echo off
setlocal
cd /d "%~dp0.."
set "PYTHONPATH=%CD%\src;%PYTHONPATH%"
python scripts\predixai_live_evidence_db_bridge.py %*
