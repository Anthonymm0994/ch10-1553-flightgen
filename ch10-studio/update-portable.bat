@echo off
echo Updating portable app...

cd /d "%~dp0"

if not exist src-tauri\target\release\ch10-studio.exe (
    echo ERROR: No release build found. Run build-portable.bat first
    exit /b 1
)

copy /Y src-tauri\target\release\ch10-studio.exe portable\CH10-Studio-Portable\
echo Updated ch10-studio.exe

if exist src-tauri\binaries\ch10gen.exe (
    if not exist portable\CH10-Studio-Portable\binaries mkdir portable\CH10-Studio-Portable\binaries
    copy /Y src-tauri\binaries\ch10gen.exe portable\CH10-Studio-Portable\binaries\
    echo Updated ch10gen.exe
)

echo.
echo Update complete!
pause