@echo off
setlocal
cd /d "%~dp0.."
python scripts\predixai_runtime_status.py %*
