# Test Coverage Matrix

## Test Suite Overview
Test coverage for ch10-1553-flightgen project.

## Coverage by Module

### Core Modules

| Module | Coverage | Test Files | Status |
|--------|----------|------------|--------|
| `ch10gen/config.py` | ✅ High | `test_config.py` | 13/13 ✅ |
| `ch10gen/encode1553.py` | ✅ High | `test_encode1553.py`, `test_icd_edge_cases.py` | 16/16 ✅ |
| `ch10gen/flight_profile.py` | ⚠️ Medium | `test_profile.py` | Needs expansion |
| `ch10gen/schedule.py` | ⚠️ Medium | `test_schedule.py` | Needs edge cases |
| `ch10gen/ch10_writer.py` | ⚠️ Low | `test_packet_accumulator.py` | Needs direct tests |
| `ch10gen/icd.py` | ✅ High | `test_icd.py`, `test_icd_edge_cases.py` | Good coverage |
| `ch10gen/errors.py` | ⚠️ Medium | `test_errors_simple.py` | Needs expansion |
| `ch10gen/validate.py` | ❌ Low | `test_wire_invariants.py` | 29% - needs work |
| `ch10gen/writer_backend.py` | ❌ Very Low | None | 14% - critical gap |

### RWR Modules

| Module | Coverage | Test Files | Status |
|--------|----------|------------|--------|
| `ch10gen/rwr_sensor.py` | ⚠️ Medium | `test_rwr_truth.py` | Needs sensor tests |
| `ch10gen/rwr_effects.py` | ✅ High | `test_rwr_effects.py` | Good coverage |
| `ch10gen/rwr_builder.py` | ⚠️ Low | `test_rwr_build_roundtrip.py` | Needs expansion |

## Test Categories

### ✅ Unit Tests (Strong)
- [x] Configuration merging - 13 tests
- [x] BNR/BCD encoding - 16 tests  
- [x] Packet structure - 6 tests
- [x] Wire invariants - 7 tests
- [x] Float encoding - multiple tests
- [x] Status word flags - complete

### ⚠️ Integration Tests (Medium)
- [x] 15s scenario generation
- [x] IPTS monotonicity
- [x] Packet type verification
- [ ] Multi-bus coordination
- [ ] Long duration scenarios
- [ ] Error injection scenarios

### ✅ Performance Tests (Good)
- [x] Message generation rate (>50k msg/s)
- [x] File write speed (<5s for 60s)
- [x] Memory stability
- [x] Large ICD handling
- [ ] Streaming performance
- [ ] Concurrent operations

### ❌ End-to-End Tests (Gaps)
- [ ] Full pipeline: ICD → Schedule → Write → Validate
- [ ] Round-trip: Write → Read → Compare
- [ ] External tool validation
- [ ] Cross-platform compatibility

## Priority Test Gaps

### 🔴 Critical (Must Fix)
1. **writer_backend.py** - Only 14% coverage, core abstraction
2. **validate.py** - Only 29% coverage, critical for verification
3. **PyChapter10 compatibility** - 7 failing tests

### 🟡 Important (Should Fix)
1. **Error injection** - More error scenarios
2. **Schedule edge cases** - Frame overflow, timing conflicts
3. **Flight profile** - Extreme maneuvers, edge conditions

### 🟢 Nice to Have
1. **CLI tests** - More command combinations
2. **TMATS generation** - Field variations
3. **Report generation** - JSON/CSV export

## Test Metrics Summary

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| Total Tests | 302 | 400+ | 75% |
| Pass Rate | 89% | 95%+ | ⚠️ |
| Coverage | 71.7% | 85%+ | ⚠️ |
| Categories | 6/10 | 10/10 | ⚠️ |
| Performance | ✅ | ✅ | ✅ |

## Next Actions

1. **Immediate**: Fix failing wire invariant tests
2. **High Priority**: Add writer_backend tests
3. **Medium Priority**: Expand validation coverage
4. **Ongoing**: Add edge cases to all modules

---
*Last Updated: 2025-01-20*
*Auto-generated from test suite analysis*
