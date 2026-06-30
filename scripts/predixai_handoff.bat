@echo off
setlocal
cd /d "%~dp0.."
python scripts\predixai_handoff_runner.py %*
