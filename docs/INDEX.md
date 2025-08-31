# CH10 Generator Documentation Index

Welcome to the CH10 Generator documentation! This index helps you find the right documentation for your needs.

## 🚀 Getting Started

- **[Quick Start Guide](QUICK_START.md)** - Get up and running in 5 minutes
- **[Configuration Guide](CONFIGURATION.md)** - Learn YAML configuration for ICDs and scenarios
- **[API Reference](API.md)** - Complete API documentation for developers

## 📖 Core Documentation

### System Design
- **[Architecture](ARCHITECTURE.md)** - System design and component overview
- **[Dependencies and Tools](DEPENDENCIES_AND_TOOLS.md)** - External tools and libraries used

### Usage Guides
- **[Testing Guide](TESTING.md)** - How to run and write tests
- **[TShark Validation](TSHARK_VALIDATION.md)** - Validating CH10 files with Wireshark/TShark
- **[Build Guide](BUILD.md)** - Building the application
- **[Troubleshooting](TROUBLESHOOTING.md)** - Common issues and solutions

### Reference Materials
- **[MIL-STD-1553 Document Links](MIL-STD-1553%20Software-Related%20Document%20Links.md)** - Standards and specifications
- **[Open-Source Tools](Open-Source%20Tools%20for%20MIL-STD-1553%20and%20IRIG%20106%20Chapter%2010%20Data.md)** - Related tools and projects

## 📚 Documentation by User Role

### For Developers
1. Start with [Quick Start](QUICK_START.md)
2. Review [Architecture](ARCHITECTURE.md)
3. Study [API Reference](API.md)
4. Learn [Testing](TESTING.md)

### For Test Engineers
1. Read [Configuration Guide](CONFIGURATION.md)
2. Understand [TShark Validation](TSHARK_VALIDATION.md)
3. Review [Troubleshooting](TROUBLESHOOTING.md)

### For System Administrators
1. Follow [Build Guide](BUILD.md)
2. Check [Dependencies](DEPENDENCIES_AND_TOOLS.md)
3. Review [Troubleshooting](TROUBLESHOOTING.md)

## 🔑 Key Features Documentation

### Bitfield Packing
- Configuration: See [CONFIGURATION.md#bitfield-packing](CONFIGURATION.md)
- API: See [API.md#bitfield-functions](API.md)
- Troubleshooting: See [TROUBLESHOOTING.md#bitfield-packing-issues](TROUBLESHOOTING.md)

### Error Injection
- Configuration: See [CONFIGURATION.md#error-injection](CONFIGURATION.md)
- API: See [API.md#error-injection](API.md)

### PCAP Export
- API: See [API.md#pcap-export](API.md)
- Usage: See [Quick Start](QUICK_START.md)

## 📋 Quick Reference

### Command Line Usage
```bash
# Check ICD validity
python -m ch10gen check-icd icd/nav_icd.yaml

# Generate CH10 file
python -m ch10gen build \
    --scenario scenarios/test_scenario.yaml \
    --icd icd/nav_icd.yaml \
    --out output.ch10 \
    --duration 60

# Validate CH10 file
python -m ch10gen validate output.ch10
```

### Python API Usage
```python
from ch10gen.icd import load_icd
from ch10gen.ch10_writer import write_ch10_file

# Load configurations
icd = load_icd('icd/nav_icd.yaml')

# Generate CH10 file
write_ch10_file(
    output_path='output.ch10',
    scenario={'duration_s': 60, 'seed': 12345},
    icd=icd
)
```

## 📊 Documentation Coverage

| Component | Guide | API | Examples | Tests |
|-----------|-------|-----|----------|-------|
| ICD Definition | ✅ | ✅ | ✅ | ✅ |
| Scenario Config | ✅ | ✅ | ✅ | ✅ |
| Bitfield Packing | ✅ | ✅ | ✅ | ✅ |
| CH10 Generation | ✅ | ✅ | ✅ | ✅ |
| Validation | ✅ | ✅ | ✅ | ✅ |
| Error Injection | ✅ | ✅ | ✅ | ✅ |
| PCAP Export | ✅ | ✅ | ✅ | ✅ |
| GUI Application | ✅ | ⚠️ | ✅ | ⚠️ |

Legend: ✅ Complete | ⚠️ Partial | ❌ Missing

## 🔍 Search Tips

Looking for something specific? Use these keywords:

- **Bitfield**: mask, shift, packing, word_index
- **Encoding**: BNR16, u16, i16, float32_split
- **1553**: RT, SA, TR, BC2RT, RT2BC
- **CH10**: IRIG-106, TMATS, packet
- **Validation**: TShark, Wireshark, PyChapter10
- **Performance**: optimization, memory, speed
- **Errors**: troubleshooting, debug, ValueError

## 📝 Documentation Standards

All documentation follows these standards:
- **Markdown formatting** with clear headers
- **Code examples** in fenced blocks with syntax highlighting
- **Tables** for structured data
- **Links** to related documentation
- **Version information** where applicable

## 🆘 Need Help?

Can't find what you're looking for?

1. Check [Troubleshooting](TROUBLESHOOTING.md) for common issues
2. Search documentation with keywords above
3. Review examples in `/examples` directory
4. Check test files in `/tests` for usage patterns

## 📈 Documentation Metrics

- **Total Documents**: 11
- **Total Lines**: ~3,500
- **Code Examples**: 100+
- **API Functions**: 50+
- **Configuration Options**: 40+

Last Updated: 2024-01-20
