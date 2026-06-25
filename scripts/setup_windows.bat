@echo off
setlocal

cd /d "%~dp0.."

echo PredixAI Windows 10 setup
echo Repository: %CD%

set "PYTHON_CMD=python"
python --version >nul 2>nul
if errorlevel 1 (
    py -3 --version >nul 2>nul
    if errorlevel 1 (
        echo Python 3.11 or newer was not found.
        exit /b 1
    )
    set "PYTHON_CMD=py -3"
)

%PYTHON_CMD% --version
%PYTHON_CMD% -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)"
if errorlevel 1 (
    echo Python 3.11 or newer is required.
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 exit /b 1
)

set "VENV_PYTHON=.venv\Scripts\python.exe"

"%VENV_PYTHON%" -m pip --version
if errorlevel 1 exit /b 1

if exist requirements.txt (
    "%VENV_PYTHON%" -m pip install -r requirements.txt
    if errorlevel 1 exit /b 1
)

for %%D in (config data logs captures assets tests) do (
    if not exist "%%D" mkdir "%%D"
    if errorlevel 1 exit /b 1
)

"%VENV_PYTHON%" -m compileall -q predixai src
if errorlevel 1 exit /b 1

"%VENV_PYTHON%" -m predixai.main
if errorlevel 1 exit /b 1

echo PredixAI Windows 10 setup completed.
exit /b 0
