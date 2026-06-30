@echo off
setlocal
cd /d "%~dp0.."
python scripts\predixai_agent_runner.py %*
