@echo off
setlocal
cd /d %~dp0..
python tools\openclaw\openclaw_runner.py --task validate_base
endlocal

