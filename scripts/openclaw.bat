@echo off
setlocal
cd /d %~dp0..
python tools\openclaw\openclaw_runner.py %*
endlocal

