# CH10 Studio Portable Application Builder
# Builds a portable Windows application with all dependencies

param(
    [switch]$SkipPython,
    [switch]$SkipFrontend,
    [switch]$Debug
)

Write-Host "CH10 Studio Portable Builder" -ForegroundColor Cyan
Write-Host "=============================" -ForegroundColor Cyan

# Configuration
$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$studioRoot = $PSScriptRoot
$pythonRoot = Join-Path $projectRoot "ch10gen"
$outputDir = Join-Path $studioRoot "portable"
$distDir = Join-Path $outputDir "CH10-Studio-Portable"

# Step 1: Build Python CLI Binary
if (-not $SkipPython) {
    Write-Host "`n[1/5] Building Python CLI Binary..." -ForegroundColor Yellow
    
    # Create binaries directory
    $binDir = Join-Path $studioRoot "src-tauri\binaries"
    if (-not (Test-Path $binDir)) {
        New-Item -ItemType Directory -Path $binDir -Force | Out-Null
    }
    
    # Build with PyInstaller
    Push-Location $projectRoot
    try {
        Write-Host "  Installing PyInstaller..." -ForegroundColor Gray
        pip install pyinstaller --quiet
        
        Write-Host "  Building ch10gen.exe..." -ForegroundColor Gray
        pyinstaller --onefile `
            --name ch10gen `
            --distpath "$binDir" `
            --workpath "build\pyinstaller" `
            --specpath "build\pyinstaller" `
            --noconsole `
            --clean `
            --add-data "icd;icd" `
            --add-data "scenarios;scenarios" `
            --hidden-import ch10gen `
            --hidden-import click `
            --hidden-import pychapter10 `
            --hidden-import numpy `
            ch10gen\__main__.py
        
        # Rename for different platforms if needed
        if (Test-Path "$binDir\ch10gen.exe") {
            Copy-Item "$binDir\ch10gen.exe" "$binDir\ch10gen-x86_64-pc-windows-msvc.exe" -Force
            Write-Host "  ✓ Python CLI built successfully" -ForegroundColor Green
        } else {
            throw "Failed to build Python CLI"
        }
    }
    finally {
        Pop-Location
    }
} else {
    Write-Host "`n[1/5] Skipping Python CLI build (using existing binary)" -ForegroundColor Gray
}

# Step 2: Install Node Dependencies
Write-Host "`n[2/5] Installing Node dependencies..." -ForegroundColor Yellow
Push-Location $studioRoot
try {
    npm install --silent
    Write-Host "  ✓ Dependencies installed" -ForegroundColor Green
}
finally {
    Pop-Location
}

# Step 3: Build Frontend
if (-not $SkipFrontend) {
    Write-Host "`n[3/5] Building frontend..." -ForegroundColor Yellow
    Push-Location $studioRoot
    try {
        npm run build
        Write-Host "  ✓ Frontend built" -ForegroundColor Green
    }
    finally {
        Pop-Location
    }
} else {
    Write-Host "`n[3/5] Skipping frontend build (using existing dist)" -ForegroundColor Gray
}

# Step 4: Build Tauri Application
Write-Host "`n[4/5] Building Tauri application..." -ForegroundColor Yellow
Push-Location $studioRoot
try {
    if ($Debug) {
        npm run tauri build -- --debug
    } else {
        npm run tauri build
    }
    Write-Host "  ✓ Tauri application built" -ForegroundColor Green
}
finally {
    Pop-Location
}

# Step 5: Create Portable Package
Write-Host "`n[5/5] Creating portable package..." -ForegroundColor Yellow

# Clean output directory
if (Test-Path $distDir) {
    Remove-Item -Recurse -Force $distDir
}
New-Item -ItemType Directory -Path $distDir -Force | Out-Null

# Find the built executable
$tauriRelease = Join-Path $studioRoot "src-tauri\target\release"
$exePath = Join-Path $tauriRelease "CH10 Studio.exe"

if (-not (Test-Path $exePath)) {
    # Try with underscores
    $exePath = Join-Path $tauriRelease "ch10_studio.exe"
}

if (-not (Test-Path $exePath)) {
    throw "Built executable not found. Expected at: $exePath"
}

# Copy main executable
Write-Host "  Copying main executable..." -ForegroundColor Gray
Copy-Item $exePath "$distDir\CH10-Studio.exe"

# Copy runtime dependencies if they exist
$depsToCheck = @(
    "*.dll",
    "resources"
)

foreach ($dep in $depsToCheck) {
    $depPath = Join-Path $tauriRelease $dep
    if (Test-Path $depPath) {
        Write-Host "  Copying $dep..." -ForegroundColor Gray
        Copy-Item $depPath $distDir -Recurse -Force
    }
}

# Copy Python dependencies
$pythonDeps = Join-Path $distDir "python"
New-Item -ItemType Directory -Path $pythonDeps -Force | Out-Null

# Copy ICD and scenario files
Write-Host "  Copying ICD files..." -ForegroundColor Gray
Copy-Item (Join-Path $projectRoot "icd") $pythonDeps -Recurse -Force

Write-Host "  Copying scenario files..." -ForegroundColor Gray
Copy-Item (Join-Path $projectRoot "scenarios") $pythonDeps -Recurse -Force



# Create README
Write-Host "  Creating README..." -ForegroundColor Gray
@"
CH10 Studio - Portable Edition
==============================

This is a portable version of CH10 Studio that can run without installation.

USAGE:
------
1. Extract this folder to any location
2. Run CH10-Studio.exe
3. The application will start with the GUI

FEATURES:
---------
- Generate CH10 files with 1553 data
- Validate and inspect CH10 files
- Export to PCAP format
- Timeline viewer for 1553 messages

FILES:
------
- CH10-Studio.exe: Main application
- python/: Python runtime and dependencies
- icd/: ICD definition files
- scenarios/: Scenario configuration files

REQUIREMENTS:
-------------
- Windows 10 or later
- 100MB free disk space

NOTES:
------
- Generated files are saved to the 'out' folder by default
- Settings are stored in %APPDATA%\CH10-Studio

Version: $(Get-Date -Format "yyyy-MM-dd")
"@ | Out-File "$distDir\README.txt" -Encoding UTF8

# Summary
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Build Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Portable package created at:" -ForegroundColor White
Write-Host "  Directory: $distDir" -ForegroundColor Yellow

$dirSize = (Get-ChildItem $distDir -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB
Write-Host "`nPackage size: $([math]::Round($dirSize, 2)) MB" -ForegroundColor Gray

Write-Host "`nTo run the application:" -ForegroundColor White
Write-Host "  Run CH10-Studio.exe from the portable folder" -ForegroundColor Gray
