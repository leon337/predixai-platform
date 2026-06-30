@echo off
setlocal
cd /d "%~dp0.."
python scripts\predixai_task_protocol.py %*
