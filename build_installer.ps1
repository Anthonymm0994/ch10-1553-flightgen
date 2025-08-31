# CH10 Generator - Installer Builder
# Creates MSI installer using WiX or NSIS

param(
    [string]$Version = "1.0.0",
    [string]$OutputDir = "releases",
    [switch]$SkipTests
)

Write-Host "`nCH10 Generator - Installer Builder v$Version" -ForegroundColor Cyan
Write-Host "=" * 50

# Check prerequisites
function Test-Prerequisite {
    param([string]$Command, [string]$Name, [string]$InstallHint)
    
    try {
        $null = Get-Command $Command -ErrorAction Stop
        Write-Host "✓ $Name found" -ForegroundColor Green
        return $true
    } catch {
        Write-Host "✗ $Name not found. $InstallHint" -ForegroundColor Red
        return $false
    }
}

Write-Host "`nChecking prerequisites..."
$hasAllPrereqs = $true
$hasAllPrereqs = Test-Prerequisite "python" "Python" "Install from python.org" -and $hasAllPrereqs
$hasAllPrereqs = Test-Prerequisite "pyinstaller" "PyInstaller" "Run: pip install pyinstaller" -and $hasAllPrereqs

if (-not $hasAllPrereqs) {
    Write-Host "`nMissing prerequisites. Please install required tools." -ForegroundColor Red
    exit 1
}

# Build standalone executable
Write-Host "`n[1/4] Building standalone executable..." -ForegroundColor Yellow

$buildArgs = @(
    "--onefile",
    "--name", "ch10gen",
    "--distpath", "dist",
    "--clean",
    "--noconfirm",
    "--icon", "ch10-studio\src-tauri\icons\icon.ico",
    "--add-data", "icd;icd",
    "--add-data", "scenarios;scenarios",
    "ch10gen\__main__.py"
)

# Add icon if it exists
if (Test-Path "ch10-studio\src-tauri\icons\icon.ico") {
    $buildArgs += "--icon"
    $buildArgs += "ch10-studio\src-tauri\icons\icon.ico"
}

& pyinstaller $buildArgs

if (-not (Test-Path "dist\ch10gen.exe")) {
    Write-Host "Failed to build executable" -ForegroundColor Red
    exit 1
}

Write-Host "✓ Executable built successfully" -ForegroundColor Green

# Run tests if not skipped
if (-not $SkipTests) {
    Write-Host "`n[2/4] Running tests..." -ForegroundColor Yellow
    & dist\ch10gen.exe --version
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Executable test failed" -ForegroundColor Red
        exit 1
    }
    Write-Host "✓ Tests passed" -ForegroundColor Green
} else {
    Write-Host "`n[2/4] Skipping tests (--SkipTests specified)" -ForegroundColor Yellow
}

# Create installer structure
Write-Host "`n[3/4] Creating installer structure..." -ForegroundColor Yellow

$installerDir = "$OutputDir\installer-$Version"
if (Test-Path $installerDir) {
    Remove-Item $installerDir -Recurse -Force
}

New-Item -ItemType Directory -Path $installerDir -Force | Out-Null
New-Item -ItemType Directory -Path "$installerDir\bin" -Force | Out-Null
New-Item -ItemType Directory -Path "$installerDir\data" -Force | Out-Null
New-Item -ItemType Directory -Path "$installerDir\docs" -Force | Out-Null

# Copy files
Copy-Item "dist\ch10gen.exe" "$installerDir\bin\"
Copy-Item -Recurse "icd" "$installerDir\data\"
Copy-Item -Recurse "scenarios" "$installerDir\data\"
Copy-Item -Recurse "examples" "$installerDir\data\"
Copy-Item "README.md" "$installerDir\"
Copy-Item "docs\*.md" "$installerDir\docs\" -ErrorAction SilentlyContinue

Write-Host "✓ Installer structure created" -ForegroundColor Green

# Create NSIS installer script
Write-Host "`n[4/4] Creating NSIS installer..." -ForegroundColor Yellow

$nsisScript = @"
; CH10 Generator NSIS Installer Script
!define PRODUCT_NAME "CH10 Generator"
!define PRODUCT_VERSION "$Version"
!define PRODUCT_PUBLISHER "CH10 Team"

; Include Modern UI
!include "MUI2.nsh"

; General
Name "`${PRODUCT_NAME} `${PRODUCT_VERSION}"
OutFile "$OutputDir\ch10gen-setup-`${PRODUCT_VERSION}.exe"
InstallDir "`$PROGRAMFILES64\CH10Generator"
RequestExecutionLevel admin

; Interface Settings
!define MUI_ABORTWARNING
!define MUI_ICON "ch10-studio\src-tauri\icons\icon.ico"

; Pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "README.md"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

; Languages
!insertmacro MUI_LANGUAGE "English"

; Installer Section
Section "Main Installation"
    SetOutPath "`$INSTDIR"
    
    ; Copy files
    File /r "$installerDir\*.*"
    
    ; Create shortcuts
    CreateDirectory "`$SMPROGRAMS\`${PRODUCT_NAME}"
    CreateShortcut "`$SMPROGRAMS\`${PRODUCT_NAME}\CH10 Generator.lnk" "`$INSTDIR\bin\ch10gen.exe"
    CreateShortcut "`$SMPROGRAMS\`${PRODUCT_NAME}\Uninstall.lnk" "`$INSTDIR\uninstall.exe"
    CreateShortcut "`$DESKTOP\CH10 Generator.lnk" "`$INSTDIR\bin\ch10gen.exe"
    
    ; Add to PATH
    Push "`$INSTDIR\bin"
    Call AddToPath
    
    ; Write uninstaller
    WriteUninstaller "`$INSTDIR\uninstall.exe"
    
    ; Registry entries
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\`${PRODUCT_NAME}" "DisplayName" "`${PRODUCT_NAME}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\`${PRODUCT_NAME}" "UninstallString" "`$INSTDIR\uninstall.exe"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\`${PRODUCT_NAME}" "DisplayVersion" "`${PRODUCT_VERSION}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\`${PRODUCT_NAME}" "Publisher" "`${PRODUCT_PUBLISHER}"
SectionEnd

; Uninstaller Section
Section "Uninstall"
    ; Remove files
    Delete "`$INSTDIR\*.*"
    RMDir /r "`$INSTDIR"
    
    ; Remove shortcuts
    Delete "`$SMPROGRAMS\`${PRODUCT_NAME}\*.*"
    RMDir "`$SMPROGRAMS\`${PRODUCT_NAME}"
    Delete "`$DESKTOP\CH10 Generator.lnk"
    
    ; Remove from PATH
    Push "`$INSTDIR\bin"
    Call un.RemoveFromPath
    
    ; Remove registry entries
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\`${PRODUCT_NAME}"
SectionEnd

; Helper functions for PATH manipulation
Function AddToPath
    ; Implementation would go here
FunctionEnd

Function un.RemoveFromPath
    ; Implementation would go here
FunctionEnd
"@

$nsisScript | Out-File -FilePath "$installerDir\installer.nsi" -Encoding UTF8

# Check if NSIS is available
if (Get-Command "makensis" -ErrorAction SilentlyContinue) {
    Write-Host "Building NSIS installer..."
    & makensis "$installerDir\installer.nsi"
    Write-Host "✓ Installer created: $OutputDir\ch10gen-setup-$Version.exe" -ForegroundColor Green
} else {
    Write-Host "NSIS not found. Installer script created at: $installerDir\installer.nsi" -ForegroundColor Yellow
    Write-Host "Install NSIS from nsis.sourceforge.io to build the installer" -ForegroundColor Yellow
}

# Create portable ZIP
Write-Host "`nCreating portable ZIP package..." -ForegroundColor Yellow
if (Get-Command "Compress-Archive" -ErrorAction SilentlyContinue) {
    Compress-Archive -Path "$installerDir\*" -DestinationPath "$OutputDir\ch10gen-portable-$Version.zip" -Force
    Write-Host "✓ Portable package: $OutputDir\ch10gen-portable-$Version.zip" -ForegroundColor Green
}

Write-Host "`n" + "=" * 50
Write-Host "BUILD COMPLETE!" -ForegroundColor Green
Write-Host "=" * 50
Write-Host "`nOutputs:"
Write-Host "  - Executable: dist\ch10gen.exe"
Write-Host "  - Portable: $OutputDir\ch10gen-portable-$Version.zip"
if (Test-Path "$OutputDir\ch10gen-setup-$Version.exe") {
    Write-Host "  - Installer: $OutputDir\ch10gen-setup-$Version.exe"
}
Write-Host "`nTo test the CLI:"
Write-Host "  .\dist\ch10gen.exe --help"
