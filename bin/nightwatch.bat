@echo off
REM =============================================================================
REM NIGHTWATCH Launcher Script (Windows)
REM =============================================================================
REM Launches the NIGHTWATCH autonomous observatory system.
REM
REM Usage:
REM   bin\nightwatch.bat                    - Run with defaults
REM   bin\nightwatch.bat --config C:\path\to\config.yaml
REM   bin\nightwatch.bat --dry-run          - Validate config only
REM   bin\nightwatch.bat --help             - Show help
REM
REM Environment:
REM   NIGHTWATCH_CONFIG    - Path to configuration file
REM   NIGHTWATCH_LOG_LEVEL - Logging level (DEBUG, INFO, WARNING, ERROR)
REM   VIRTUAL_ENV          - Python virtual environment path
REM =============================================================================

setlocal EnableDelayedExpansion

REM Determine script directory
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."

REM Change to project root
pushd "%PROJECT_ROOT%"

REM Check for virtual environment
if defined VIRTUAL_ENV (
    echo Using virtual environment: %VIRTUAL_ENV%
    goto :find_python
)

REM Look for common venv locations
if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
    echo Activated virtual environment: .venv
    goto :find_python
)

if exist "venv\Scripts\activate.bat" (
    call "venv\Scripts\activate.bat"
    echo Activated virtual environment: venv
    goto :find_python
)

echo Warning: No virtual environment found. Using system Python.

:find_python
REM Find Python executable
set "PYTHON_CMD="

where python3 >nul 2>&1
if %ERRORLEVEL% equ 0 (
    set "PYTHON_CMD=python3"
    goto :check_version
)

where python >nul 2>&1
if %ERRORLEVEL% equ 0 (
    set "PYTHON_CMD=python"
    goto :check_version
)

echo Error: Python not found. Please install Python 3.11+
exit /b 1

:check_version
REM Check Python version
for /f "tokens=*" %%i in ('!PYTHON_CMD! -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"') do set "PY_VERSION=%%i"

for /f "tokens=1,2 delims=." %%a in ("%PY_VERSION%") do (
    set "PY_MAJOR=%%a"
    set "PY_MINOR=%%b"
)

if %PY_MAJOR% LSS 3 (
    echo Error: Python 3.11+ required ^(found %PY_VERSION%^)
    exit /b 1
)

if %PY_MAJOR% EQU 3 (
    if %PY_MINOR% LSS 11 (
        echo Error: Python 3.11+ required ^(found %PY_VERSION%^)
        exit /b 1
    )
)

REM Build arguments
set "ARGS=%*"

REM Add config from environment if not specified
if defined NIGHTWATCH_CONFIG (
    echo %ARGS% | findstr /C:"--config" /C:"-c" >nul
    if errorlevel 1 (
        set "ARGS=!ARGS! --config %NIGHTWATCH_CONFIG%"
    )
)

REM Add log level from environment if not specified
if defined NIGHTWATCH_LOG_LEVEL (
    echo %ARGS% | findstr /C:"--log-level" /C:"-l" >nul
    if errorlevel 1 (
        set "ARGS=!ARGS! --log-level %NIGHTWATCH_LOG_LEVEL%"
    )
)

REM Run NIGHTWATCH
%PYTHON_CMD% -m nightwatch.main %ARGS%

REM Restore directory
popd

endlocal
