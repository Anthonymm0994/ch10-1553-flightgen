# Build Guide

This guide covers building the CH10 Generator for local use.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Building the CLI](#building-the-cli)
- [Building the GUI](#building-the-gui)
- [Portable Builds](#portable-builds)
- [Build Scripts](#build-scripts)

## Prerequisites

### Required Software
- **Python 3.8+**: Core runtime environment
- **Git**: Source code management
- **Build Tools**: Platform-specific compilation tools

### Windows
- Visual Studio Build Tools or Visual Studio Community
- Git Bash (recommended terminal)

### Linux
- `build-essential` package
- `python3-dev` package

### macOS
- Xcode Command Line Tools
- Homebrew (optional, for dependencies)

## Building the CLI

### Method 1: Python Package
```bash
# Install in development mode
pip install -e .

# Run directly
python -m ch10gen --help
```

### Method 2: PyInstaller (Portable)
```bash
# Install PyInstaller
pip install pyinstaller

# Build executable
pyinstaller --onefile --name ch10gen-cli ch10gen/__main__.py

# Run from dist folder
./dist/ch10gen-cli --help
```

### Method 3: cx_Freeze
```bash
# Install cx_Freeze
pip install cx_Freeze

# Build using setup.py
python setup.py build

# Run from build folder
./build/exe.linux-x86_64-3.8/ch10gen --help
```

## Building the GUI

### Prerequisites
- **Node.js 16+**: Frontend build tools
- **Rust**: Tauri backend compilation

### Build Steps
```bash
# Install frontend dependencies
cd ch10-studio
npm install

# Build frontend
npm run build

# Build Tauri application
npm run tauri build

# Output in src-tauri/target/release/
```

### Development Mode
```bash
# Start development server
npm run tauri dev
```

## Portable Builds

### Windows
```bash
# Using build script
./build_releases.bat

# Manual PyInstaller
pyinstaller --onefile --windowed --name ch10gen ch10gen/__main__.py
```

### Linux
```bash
# Create AppImage
./build_releases.sh

# Manual build
pyinstaller --onefile --name ch10gen ch10gen/__main__.py
```

### macOS
```bash
# Create .app bundle
./build_releases.sh

# Manual build
pyinstaller --onefile --windowed --name ch10gen ch10gen/__main__.py
```

## Build Scripts

### Windows (build_releases.bat)
```batch
@echo off
echo Building CH10 Generator...

REM Build CLI
pyinstaller --onefile --name ch10gen-cli ch10gen/__main__.py

REM Build GUI
cd ch10-studio
npm run build
npm run tauri build

echo Build complete!
```

### PowerShell (build_installer.ps1)
```powershell
# Build MSI installer
# Requires WiX Toolset
# See WiX documentation for details
```

### Linux/macOS (build_releases.sh)
```bash
#!/bin/bash
echo "Building CH10 Generator..."

# Build CLI
pyinstaller --onefile --name ch10gen ch10gen/__main__.py

# Build GUI
cd ch10-studio
npm run build
npm run tauri build

echo "Build complete!"
```

## Build Configuration

### PyInstaller Options
- `--onefile`: Single executable
- `--windowed`: No console window (GUI)
- `--name`: Output filename
- `--icon`: Application icon
- `--add-data`: Include additional files

### Tauri Configuration
Edit `ch10-studio/src-tauri/tauri.conf.json`:
```json
{
  "build": {
    "distDir": "../dist",
    "devPath": "http://localhost:3000"
  },
  "bundle": {
    "identifier": "com.example.ch10gen",
    "icon": ["icons/32x32.png", "icons/128x128.png"]
  }
}
```

## Troubleshooting

### Common Issues

#### PyInstaller Fails
- Ensure all dependencies are installed
- Check Python path and environment
- Try `--debug all` for verbose output

#### Tauri Build Fails
- Verify Rust toolchain: `rustc --version`
- Check Node.js version: `node --version`
- Ensure frontend build succeeds first

#### Missing Dependencies
- Run `pip install -r requirements.txt`
- Check platform-specific requirements
- Verify build tools installation

### Performance Optimization

#### Build Time
- Use `--noconfirm` for PyInstaller
- Parallel compilation with `-j` flag
- Incremental builds when possible

#### Executable Size
- Exclude unnecessary modules
- Use `--exclude-module` selectively
- Compress with UPX (optional)

## Next Steps

After building:
1. Test the executable thoroughly
2. Validate generated CH10 files
3. Package with documentation
4. Distribute to users

For development:
1. Use development mode for faster iteration
2. Enable debug logging
3. Test on target platforms
4. Monitor build performance
