# Changelog

All notable changes to the CH10 Generator project are documented here.

## [2.0.0] - 2024-12-29

### Added
- Scenario-driven data generation system with 13+ generator types
- Mathematical expression evaluation with field references
- Waveform generators (sine, cosine, square, sawtooth, ramp)
- Multiple random distributions (uniform, normal, multimodal)
- Cross-message field references in expressions
- Performance improvements supporting 1000+ messages/second
- Support for 70k+ line ICDs
- Comprehensive test suite for all generators
- XML to YAML converter improvements
- Breaking changes documentation

### Changed
- **BREAKING**: Scenario format now uses `defaults` section instead of root-level `data_mode`
- **BREAKING**: ICDs no longer support `src: random` field
- Default bus changed from 'A' to 'B' in XML converter
- XML converter now uses filename as ICD name
- Improved error messages in GUI

### Removed
- Old `RandomDataGenerator` class (replaced by modular system)
- `src: random` field support in ICDs

### Fixed
- GUI error display now shows actual error messages
- Test suite compatibility with new system
- Performance issues with large ICDs

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2024-01-20

### Added
- **Bitfield Packing Support** - Major feature addition
  - Support for `mask` and `shift` fields in YAML word definitions
  - Multiple fields can be packed into single 16-bit words
  - Comprehensive validation for bitfield overlaps
  - Scaling and offset support for bitfield values
  - 25+ tests covering all bitfield scenarios
  
- **Documentation**
  - `BUILD.md` - Complete build guide for CLI and GUI
  - `TROUBLESHOOTING.md` - Common issues and solutions
  - `INDEX.md` - Documentation overview and navigation
  - Updated all existing documentation for accuracy

- **Build Scripts**
  - `build_releases.bat` - Windows batch script for releases
  - `build_installer.ps1` - PowerShell script for MSI installer
  - `.gitignore` - Complete ignore patterns

- **Example Scripts**
  - `examples/generate_basic.py` - Basic CH10 generation
  - `examples/custom_encoding.py` - Advanced encoding examples
  - `examples/bitfield_demo.py` - Bitfield packing demonstration
  - `examples/README.md` - Examples documentation

### Changed
- **Project Structure**
  - Reorganized modules into `core/` and `utils/` subdirectories
  - Moved encoding functions to `ch10gen.core.encode1553`
  - Moved TMATS to `ch10gen.core.tmats`
  - Cleaned up root directory of test files

- **Documentation Updates**
  - Removed redundant documentation files
  - Updated README with current information
  - Fixed all code examples to use current API
  - Added bitfield documentation to Configuration Guide

- **Test Improvements**
  - Fixed CLI test for Windows compatibility
  - Added bitfield tests
  - Improved TShark validation tests
  - Fixed import paths after reorganization

### Fixed
- **Windows Compatibility**
  - Fixed PyChapter10 file handle issues
  - Added Windows-specific test skips
  - Fixed path handling for cross-platform compatibility

- **Validation Issues**
  - Fixed ICD validation for bitfield configurations
  - Improved error messages for validation failures
  - Fixed mask/shift overflow detection

- **Documentation Accuracy**
  - Updated all command examples to working versions
  - Fixed API references to match current implementation
  - Corrected file paths and imports

### Removed
- Temporary files from root directory
- Duplicate project status documents
- PDF versions of markdown documentation
- Redundant documentation files

## [1.0.0] - 2024-01-15

### Added
- **Core Functionality**
  - MIL-STD-1553 message encoding
  - IRIG-106 Chapter 10 file generation
  - YAML-based ICD configuration
  - Flight profile simulation
  - Message scheduling with major/minor frames

- **Encoding Support**
  - Unsigned 16-bit (u16)
  - Signed 16-bit (i16)
  - Binary Number Representation (BNR16)
  - 32-bit float split across words
  - BCD encoding

- **Validation**
  - PyChapter10-based validation
  - TShark/Wireshark integration
  - ICD validation
  - Scenario validation

- **Export Formats**
  - PCAP export for Wireshark
  - JSON metadata export
  - Timeline export (JSONL)

- **GUI Application**
  - CH10 Studio built with Tauri
  - React-based frontend
  - Cross-platform support

- **Testing**
  - 250+ unit tests
  - Integration tests
  - Performance tests
  - CLI tests

### Known Issues
- PyChapter10 doesn't support all packet types
- Some performance tests timeout on slow systems
- File cleanup issues on Windows with PyChapter10

## [0.9.0] - 2024-01-01

### Added
- Initial project structure
- Basic 1553 encoding
- Simple CH10 writer
- Command-line interface
- Initial documentation

### Changed
- Refactored from prototype code
- Established module structure
- Added type hints

### Fixed
- Memory leaks in writer
- Encoding edge cases

## [0.1.0] - 2023-12-15

### Added
- Project inception
- Initial prototype
- Basic proof of concept

---

## Version History Summary

| Version | Date | Major Changes |
|---------|------|---------------|
| 1.1.0 | 2024-01-20 | Bitfield packing, docs, deployment scripts |
| 1.0.0 | 2024-01-15 | First stable release with full feature set |
| 0.9.0 | 2024-01-01 | Beta release with core functionality |
| 0.1.0 | 2023-12-15 | Initial prototype |

## Upgrade Guide

### From 1.0.0 to 1.1.0

1. **Update imports for reorganized modules:**
   ```python
   # Old
   from ch10gen.encode1553 import encode_u16
   
   # New
   from ch10gen.core.encode1553 import encode_u16
   ```

2. **Use bitfield packing for efficiency:**
   ```yaml
   # Old - separate words
   words:
     - name: "status1"
       encode: "u16"
     - name: "status2"
       encode: "u16"
   
   # New - packed into one word
   words:
     - name: "status1"
       encode: "u16"
       mask: 0x00FF
       shift: 0
       word_index: 0
     - name: "status2"
       encode: "u16"
       mask: 0x00FF
       shift: 8
       word_index: 0
   ```

3. **Update CLI commands:**
   ```bash
   # Old
   ch10gen validate file.ch10
   
   # New (if ch10gen not in PATH)
   python -m ch10gen validate file.ch10
   ```

## Future Roadmap

### Version 1.2.0 (Planned)
- [ ] Linux/macOS installer support
- [ ] Performance optimizations for large files
- [ ] Additional encoding types
- [ ] Real-time streaming support

### Version 2.0.0 (Future)
- [ ] Plugin architecture
- [ ] Custom protocol support
- [ ] Multi-machine distributed processing
- [ ] Web-based interface

## Contributing

See [Contributing Guidelines](CONTRIBUTING.md) for information on:
- Code style
- Testing requirements
- Pull request process
- Issue reporting

## Support

For issues and questions:
- Check [Troubleshooting Guide](docs/TROUBLESHOOTING.md)
- Review [Documentation Index](docs/INDEX.md)
- File issues on GitHub