# CH10 Studio

Desktop app for generating Chapter 10 files with MIL-STD-1553 flight test data.

## Quick Start

**To run the portable app:**
1. Go to `portable/CH10-Studio-Portable/`
2. Double-click `ch10-studio.exe`

That's it! No installation, no batch files needed.

## For Developers

### Build from source
```bash
cd ch10-studio
build-portable.bat
```

### Update existing build
```bash
cd ch10-studio
update-portable.bat
```

## Requirements
- Windows 10/11
- Microsoft Edge WebView2 Runtime (usually pre-installed)

## Features
- **Build Tab**: Generate Chapter 10 files

- **Tools Tab**: Header patcher and validator
- **Dark Mode UI**: Modern interface

## Tech Stack
- Frontend: React + TypeScript + Tailwind CSS
- Backend: Tauri (Rust) 
- CLI: Python (ch10gen)