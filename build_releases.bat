@echo off
REM =====================================================
REM CH10 Generator - Complete Build Script
REM Builds both portable CLI and GUI with installer
REM =====================================================

echo.
echo CH10 Generator - Release Builder
echo ================================
echo.

REM Check for required tools
echo Checking requirements...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found in PATH
    exit /b 1
)

pyinstaller --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: PyInstaller not found. Install with: pip install pyinstaller
    exit /b 1
)

REM Step 1: Build standalone CLI
echo.
echo [1/3] Building standalone CLI executable...
echo ---------------------------------------------
pyinstaller --onefile ^
    --name ch10gen-cli ^
    --distpath dist ^
    --clean ^
    --noconfirm ^
    ch10gen\__main__.py

if not exist "dist\ch10gen-cli.exe" (
    echo ERROR: Failed to build CLI executable
    exit /b 1
)
echo SUCCESS: CLI built at dist\ch10gen-cli.exe

REM Step 2: Test the CLI
echo.
echo [2/3] Testing CLI executable...
echo ---------------------------------------------
dist\ch10gen-cli.exe --version
if errorlevel 1 (
    echo ERROR: CLI executable test failed
    exit /b 1
)
echo SUCCESS: CLI executable works!

REM Step 3: Build GUI with installer (if Tauri is available)
echo.
echo [3/3] Building GUI application...
echo ---------------------------------------------
if exist "ch10-studio\build-portable.bat" (
    echo Building CH10 Studio GUI...
    cd ch10-studio
    call build-portable.bat
    cd ..
    echo SUCCESS: GUI built with installer
) else (
    echo SKIP: GUI build script not found
)

REM Create release package
echo.
echo Creating release package...
echo ---------------------------------------------
if not exist "releases" mkdir releases
if not exist "releases\ch10gen-latest" mkdir releases\ch10gen-latest

REM Copy CLI
copy dist\ch10gen-cli.exe releases\ch10gen-latest\ >nul
echo - CLI executable copied

REM Copy sample files
xcopy /s /q icd releases\ch10gen-latest\icd\ >nul
xcopy /s /q scenarios releases\ch10gen-latest\scenarios\ >nul
xcopy /s /q examples releases\ch10gen-latest\examples\ >nul
echo - Sample files copied

REM Copy documentation
copy README.md releases\ch10gen-latest\ >nul
copy docs\*.md releases\ch10gen-latest\docs\ >nul 2>nul
echo - Documentation copied

REM Create batch file for easy CLI usage
echo @echo off > releases\ch10gen-latest\ch10gen.bat
echo ch10gen-cli.exe %%* >> releases\ch10gen-latest\ch10gen.bat
echo - Helper batch file created

REM Summary
echo.
echo =====================================================
echo BUILD COMPLETE!
echo =====================================================
echo.
echo Standalone CLI: releases\ch10gen-latest\ch10gen-cli.exe
echo.
echo To use the CLI:
echo   cd releases\ch10gen-latest
echo   ch10gen --help
echo.
echo To generate a CH10 file:
echo   ch10gen build --scenario scenarios\test_scenario.yaml --icd icd\nav_icd.yaml --out test.ch10
echo.
pause
