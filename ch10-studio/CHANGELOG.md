# CHANGELOG

## [0.1.0] - 2025-01-15

### Initial Release

#### Architecture Decisions
- **Tauri over Electron**: Smaller binary size, better Windows performance
- **Monaco Editor**: YAML editing experience with syntax highlighting
- **Sidecar Pattern**: ch10gen runs as separate process for stability and modularity
- **Plugin-based Shell**: Uses Tauri v2 shell plugin for secure process spawning

#### Features Implemented
- **Build Page**: Full standard CH10 generation workflow
  - File pickers for scenario/ICD/output
  - Monaco editors with syntax highlighting
  - Real-time progress tracking
  - Summary statistics display
  - Advanced configuration options

- **Dashboard**: Quick access to all major functions
  - Visual cards for navigation
  - Welcome screen with feature overview

- **Runner Panel**: Build configuration
  - Writer backend selection (irig106/pyc10)
  - Duration override
  - Advanced settings (collapsible)
  - Export options

- **Progress Tracking**: Live build monitoring
  - Console-style log output
  - Progress bar
  - Real-time statistics (packets/messages/rate)

#### UI/UX Decisions
- **Tab Navigation**: Clear separation of functions (Dashboard/Build/Tools)
- **Split Layout**: Editors on left, controls and output on right
- **Dark Theme**: Monaco editor uses VS Code dark theme
- **Responsive Grid**: Adapts to window resizing

#### Technical Implementation
- **TypeScript Strict Mode**: Full type safety
- **Path Aliases**: Clean imports with @/ prefix
- **Component Library**: shadcn/ui-inspired components
- **Tailwind CSS**: Utility-first styling approach

#### Known Limitations
- Tools page is a placeholder (coming soon)
- Charts not yet implemented
- No persistent storage of recent runs yet
- Sidecar binary needs manual placement

#### Development Setup
- Uses Vite for fast HMR
- TypeScript configuration with strict checking
- Tailwind with PostCSS processing
- Modular component structure

#### Testing Approach
- Manual testing of file operations
- Process spawning verification
- UI state management validation

#### Next Steps

- Add Recharts visualizations
- Implement Tools page functions
- Add persistent storage for recent runs
- Create Windows installer with bundled ch10gen
