@echo off
setlocal

for %%I in ("%~dp0..") do set "PROJECT_ROOT=%%~fI"
if /I "%PROJECT_ROOT%"=="%SystemRoot%\System32" (
    echo Refusing to use C:\Windows\System32 as the project root.
    exit /b 1
)

cd /d "%PROJECT_ROOT%"
if /I "%CD%"=="%SystemRoot%\System32" (
    echo Refusing to run from C:\Windows\System32.
    exit /b 1
)

if not exist "predixai_context.json" (
    echo predixai_context.json was not found in %CD%.
    echo Run this script from the PredixAI repository.
    exit /b 1
)

set "PYTHON_EXE=.venv\Scripts\python.exe"
set "PYTHON_ARGS="
if not exist "%PYTHON_EXE%" (
    python --version >nul 2>nul
    if not errorlevel 1 (
        set "PYTHON_EXE=python"
    ) else (
        py -3 --version >nul 2>nul
        if errorlevel 1 (
            echo Python 3.11 or newer was not found.
            exit /b 1
        )
        set "PYTHON_EXE=py"
        set "PYTHON_ARGS=-3"
    )
)

"%PYTHON_EXE%" %PYTHON_ARGS% -m predixai.main %*
exit /b %errorlevel%
