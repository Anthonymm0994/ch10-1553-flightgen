@echo off
REM CH10 Studio Portable Builder (Simple Batch Version)
REM Builds the portable Windows application

echo.
echo CH10 Studio Portable Builder
echo =============================
echo.

REM Step 1: Build Python CLI
echo [1/4] Building Python CLI...
cd ..
if not exist "ch10-studio\src-tauri\binaries" mkdir "ch10-studio\src-tauri\binaries"
pyinstaller --onefile --name ch10gen --distpath "ch10-studio\src-tauri\binaries" --noconsole ch10gen\__main__.py
if not exist "ch10-studio\src-tauri\binaries\ch10gen.exe" (
    echo ERROR: Failed to build Python CLI
    exit /b 1
)
copy "ch10-studio\src-tauri\binaries\ch10gen.exe" "ch10-studio\src-tauri\binaries\ch10gen-x86_64-pc-windows-msvc.exe" >nul
echo   Done.

REM Step 2: Build Frontend
echo [2/4] Building frontend...
cd ch10-studio
call npm install --silent
call npm run build
echo   Done.

REM Step 3: Build Tauri App
echo [3/4] Building Tauri application...
call npm run tauri build

REM Copy sidecars to release folder for bundling
copy "src-tauri\binaries\ch10gen.exe" "src-tauri\target\release\ch10gen.exe" >nul 2>&1
copy "src-tauri\binaries\ch10gen-x86_64-pc-windows-msvc.exe" "src-tauri\target\release\ch10gen-x86_64-pc-windows-msvc.exe" >nul 2>&1
echo   Done.

REM Step 4: Create Portable Package
echo [4/4] Creating portable package...
if not exist "portable" mkdir "portable"
if exist "portable\CH10-Studio-Portable" rmdir /s /q "portable\CH10-Studio-Portable"
mkdir "portable\CH10-Studio-Portable"

REM Copy executable
copy "src-tauri\target\release\CH10 Studio.exe" "portable\CH10-Studio-Portable\CH10-Studio.exe" >nul 2>&1
if not exist "portable\CH10-Studio-Portable\CH10-Studio.exe" (
    copy "src-tauri\target\release\ch10-studio.exe" "portable\CH10-Studio-Portable\CH10-Studio.exe" >nul 2>&1
)

REM Copy dependencies
xcopy /s /q "..\icd" "portable\CH10-Studio-Portable\icd\" >nul
xcopy /s /q "..\scenarios" "portable\CH10-Studio-Portable\scenarios\" >nul
xcopy /s /q "..\wireshark" "portable\CH10-Studio-Portable\wireshark\" >nul

REM Copy ch10gen binaries - both next to exe (for Tauri) and in binaries folder
REM Sidecars go next to the main exe for Tauri v2
copy "src-tauri\target\release\ch10gen.exe" "portable\CH10-Studio-Portable\ch10gen.exe" >nul 2>&1
copy "src-tauri\target\release\ch10gen-x86_64-pc-windows-msvc.exe" "portable\CH10-Studio-Portable\ch10gen-x86_64-pc-windows-msvc.exe" >nul 2>&1

REM Also copy to binaries folder for the sidecar path
mkdir "portable\CH10-Studio-Portable\binaries" >nul 2>&1
copy "src-tauri\binaries\ch10gen.exe" "portable\CH10-Studio-Portable\binaries\ch10gen.exe" >nul
copy "src-tauri\binaries\ch10gen-x86_64-pc-windows-msvc.exe" "portable\CH10-Studio-Portable\binaries\ch10gen-x86_64-pc-windows-msvc.exe" >nul

REM Create README
echo CH10 Studio - Portable Edition > "portable\CH10-Studio-Portable\README.txt"
echo. >> "portable\CH10-Studio-Portable\README.txt"
echo Run CH10-Studio.exe to start the application. >> "portable\CH10-Studio-Portable\README.txt"

echo.
echo ========================================
echo Build Complete!
echo ========================================
echo Portable package created at:
echo   portable\CH10-Studio-Portable\
echo.
echo To run: Execute CH10-Studio.exe
echo.