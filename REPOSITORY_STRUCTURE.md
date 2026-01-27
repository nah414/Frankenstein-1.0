# FRANKENSTEIN 1.0 - Repository Structure

**Version:** 1.0.0 - Phase 1 (Core Engine)
**Date:** January 25, 2026

---

## Directory Overview

```
Frankenstein-1.0/
│
├── 📄 Core Application Files
├── 📚 Documentation
├── 🚀 Quick Launch Scripts
├── 📦 Source Code Modules
├── 🧪 Test Suite
├── 📖 Additional Documentation
└── 🛠️ Utility Scripts
```

---

## Root Directory

### Entry Points & Launchers

| File | Purpose | Usage |
|------|---------|-------|
| `frankenstein.py` | Main application | `python frankenstein.py --widget` |
| `install_and_run.bat` | **One-click launcher** | Double-click to install & run |
| `LAUNCH_FRANKENSTEIN.bat` | Interactive mode selector | Choose mode at runtime |

### Documentation (Root Level)

| File | Purpose | Audience |
|------|---------|----------|
| `GETTING_STARTED.md` | **Quick start guide** | New users |
| `README.md` | Project overview | Everyone |
| `RELEASE_NOTES.md` | Version 1.0 release notes | Users & developers |
| `BUILD_COMPLETE.md` | Build completion summary | Developers |
| `REPOSITORY_STRUCTURE.md` | This file | Developers |

### Configuration & Metadata

| File | Purpose |
|------|---------|
| `requirements.txt` | Python dependencies |
| `LICENSE` | MIT License |
| `.gitignore` | Git ignore rules |
| `push_to_github.bat` | GitHub push script |
| `SETUP_GITHUB.md` | GitHub setup instructions |

---

## Source Code (`/core`)

**Purpose:** Core engine implementation (Phase 1)

| File | Module | Lines | Purpose |
|------|--------|-------|---------|
| `__init__.py` | Exports | 66 | Module exports and version |
| `safety.py` | Safety System | 118 | Immutable hardware protection |
| `governor.py` | Resource Governor | ~300 | Real-time monitoring & throttling |
| `memory.py` | Memory System | ~250 | Session persistence & history |
| `orchestrator.py` | Task Orchestrator | ~350 | Task queue & worker management |

**Total:** ~1,100 lines of production code

---

## Widget UI (`/widget`)

**Purpose:** Always-on-top display overlay

| File | Module | Lines | Purpose |
|------|--------|-------|---------|
| `__init__.py` | Exports | ~10 | Module initialization |
| `overlay.py` | Widget | 287 | UI overlay with live stats |

**Dependencies:** customtkinter, threading

---

## Configuration (`/configs`)

**Purpose:** Hardware-specific configurations

| File | Target Hardware | Purpose |
|------|-----------------|---------|
| `tier1_laptop.yaml` | Dell i3 8th Gen | Default config (8GB RAM, 4 cores) |

**Configuration Includes:**
- Resource limits (CPU, RAM, threads)
- Widget settings (position, transparency)
- Feature flags
- Performance targets
- Logging configuration

---

## Test Suite (`/tests`)

**Purpose:** Automated testing (78+ tests)

### Test Structure
```
tests/
├── __init__.py
└── unit/
    ├── __init__.py
    ├── test_safety.py          # 25+ tests
    ├── test_governor.py        # 15+ tests
    ├── test_memory.py          # 18+ tests
    └── test_orchestrator.py    # 20+ tests
```

### Test Coverage

| Module | Tests | Coverage Areas |
|--------|-------|----------------|
| `test_safety.py` | 25+ | Safety constraints, violations, Tier 1 compliance |
| `test_governor.py` | 15+ | Resource monitoring, throttling, lifecycle |
| `test_memory.py` | 18+ | Session state, task records, persistence |
| `test_orchestrator.py` | 20+ | Task management, priority queue, workers |

**Total:** 78+ automated tests

**Run Tests:**
```batch
cd scripts
run_tests.bat coverage
```

---

## Documentation (`/docs`)

**Purpose:** Detailed technical documentation

| File | Purpose | Audience |
|------|---------|----------|
| `TESTING.md` | Complete testing guide | Developers |
| `AUTOMATION_SETUP.md` | Automation infrastructure details | Developers |

**Cross-references:**
- Testing modes and options
- CI/CD integration examples
- Troubleshooting guides
- Best practices

---

## Utility Scripts (`/scripts`)

**Purpose:** Development and maintenance tools

### Setup & Installation

| Script | Purpose | Platform |
|--------|---------|----------|
| `setup_env.bat` | Install dependencies | Windows |

### Testing

| Script | Purpose | Platform |
|--------|---------|----------|
| `run_tests.bat` | Test runner with 5 modes | Windows |
| `test_runner.py` | Cross-platform test runner | All |

### Utilities

| Script | Purpose | Platform |
|--------|---------|----------|
| `Create_Desktop_Shortcut.bat` | Create desktop shortcut | Windows |

**Run from project root or scripts directory**

---

## Future Modules (Planned)

### Phase 2: Synthesis (`/synthesis`)
- Predictive synthesis engine
- Physics-informed models
- Classical-quantum hybrid algorithms

### Phase 3: Quantum (`/quantum`)
- IBM Quantum integration
- AWS Braket support
- Azure Quantum integration
- Local quantum simulation

### Phase 4: Agents (`/agents`)
- MCP agent framework
- Multi-agent collaboration
- Tool integration

### Additional Modules

| Directory | Purpose | Status |
|-----------|---------|--------|
| `/classical` | Classical computation | Placeholder |
| `/security` | Security features | Placeholder |

---

## Data Storage (Runtime)

**Location:** `~/.frankenstein/`

```
~/.frankenstein/
├── session.json        # Current session state
├── history/            # Task history (rolling 1000)
├── learning/           # Learned patterns (Phase 2+)
├── cache/              # Temporary cache
└── logs/               # Log files
    └── frankenstein.log
```

**Storage Limit:** 20GB maximum

---

## File Count Summary

| Category | Count | Total Lines |
|----------|-------|-------------|
| Core Modules | 4 | ~1,100 |
| Widget | 1 | 287 |
| Tests | 4 | ~650 |
| Documentation | 8 | ~2,500 |
| Scripts | 4 | ~300 |
| Config | 1 | 74 |

**Total Production Code:** ~1,400 lines
**Total Test Code:** ~650 lines
**Test/Code Ratio:** 46% (excellent coverage)

---

## Dependencies

### Runtime Dependencies
```
psutil>=5.9.0              # System monitoring
pyyaml>=6.0                # Configuration
customtkinter>=5.0.0       # Widget UI
```

### Development Dependencies
```
pytest>=7.4.0              # Testing
pytest-cov>=4.1.0          # Coverage
black>=23.0.0              # Formatting
mypy>=1.5.0                # Type checking
```

**Total:** 7 dependencies

---

## Key Features Location Map

| Feature | Implementation | Tests | Config |
|---------|---------------|-------|--------|
| Safety System | `core/safety.py` | `tests/unit/test_safety.py` | `configs/*.yaml` |
| Resource Monitor | `core/governor.py` | `tests/unit/test_governor.py` | `configs/*.yaml` |
| Memory/Persistence | `core/memory.py` | `tests/unit/test_memory.py` | `~/.frankenstein/` |
| Task Management | `core/orchestrator.py` | `tests/unit/test_orchestrator.py` | `configs/*.yaml` |
| Widget Display | `widget/overlay.py` | Manual testing | `configs/*.yaml` |

---

## Quick Navigation

### For Users
1. **Start Here:** [GETTING_STARTED.md](GETTING_STARTED.md)
2. **Project Overview:** [README.md](README.md)
3. **What's New:** [RELEASE_NOTES.md](RELEASE_NOTES.md)

### For Developers
1. **Repository Structure:** This file
2. **Testing Guide:** [docs/TESTING.md](docs/TESTING.md)
3. **Automation Details:** [docs/AUTOMATION_SETUP.md](docs/AUTOMATION_SETUP.md)
4. **Source Code:** `core/*.py`, `widget/*.py`

### Quick Access
```batch
# Launch application
install_and_run.bat

# Run tests
cd scripts && run_tests.bat coverage

# View status
python frankenstein.py --status

# Create shortcuts
scripts\Create_Desktop_Shortcut.bat
```

---

## Git Structure

### Main Branches
- `main` - Production-ready code (current)

### Commits Structure
- Phase 1 implementation commits
- Test suite commits
- Documentation commits
- Automation commits

### .gitignore Coverage
```
__pycache__/
*.pyc
.pytest_cache/
htmlcov/
.coverage
*.log
~/.frankenstein/    # User data
```

---

## CI/CD Integration Points

### GitHub Actions Ready
- Test runner: `scripts/test_runner.py`
- Requirements: `requirements.txt`
- Test command: `python test_runner.py coverage`

### Recommended Workflows
1. **Test on Push:** Run all tests
2. **Coverage Report:** Generate and upload
3. **Linting:** black, mypy checks
4. **Release:** Automated tagging

---

## Code Organization Principles

### Separation of Concerns
- **Core:** Business logic and safety
- **Widget:** UI presentation
- **Tests:** Validation
- **Docs:** Documentation
- **Scripts:** Utilities

### Singleton Pattern
- Governor: `get_governor()`
- Memory: `get_memory()`
- Orchestrator: `get_orchestrator()`
- Widget: `get_widget()`

### Immutable Safety
- `SAFETY` constant in `core/safety.py`
- Cannot be modified at runtime
- Hardware protection guarantee

---

## Metrics

### Code Quality
- **Test Coverage:** 78+ tests
- **Documentation:** Complete
- **Type Hints:** Partial (Python 3.12)
- **Linting:** Black-compatible

### Performance
- **Startup Time:** < 2 seconds
- **Resource Check:** Every 1 second
- **Widget Refresh:** Every 1 second
- **Memory Footprint:** < 50MB

### Safety
- **CPU Limit:** 80%
- **RAM Limit:** 70%
- **Thread Limit:** 3
- **Storage Limit:** 20GB

---

## Contributing

### Adding New Features
1. Create feature branch
2. Implement in appropriate module
3. Add tests to `tests/unit/`
4. Update documentation
5. Run full test suite
6. Submit PR

### Adding Tests
1. Use pytest framework
2. Follow existing test structure
3. Aim for 80%+ coverage
4. Test edge cases

### Documentation
1. Update relevant .md files
2. Add inline docstrings
3. Update RELEASE_NOTES.md
4. Keep GETTING_STARTED.md current

---

## Support Files

### Build Information
- `BUILD_COMPLETE.md` - Phase 1 completion summary
- `SETUP_GITHUB.md` - GitHub repository setup

### Scripts Helpers
- `push_to_github.bat` - Git push automation
- `scripts/setup_env.bat` - Environment setup

---

## Version Control

**Current Version:** 1.0.0
**Phase:** 1 (Core Engine)
**Status:** Production Ready ✅

**Version in Code:**
```python
# core/__init__.py
__version__ = "1.0.0-phase1"
```

---

## Summary

This repository is organized for:
- ✅ **Easy onboarding** - Clear entry points
- ✅ **Development** - Well-structured code
- ✅ **Testing** - Comprehensive test suite
- ✅ **Documentation** - Multiple guides
- ✅ **Automation** - Scripts for common tasks
- ✅ **Maintenance** - Clean separation of concerns

**Total Files:** ~30 files
**Total Directories:** 9 directories
**Documentation Files:** 8 files
**Test Files:** 4 files
**Source Files:** 6 files

---

**Last Updated:** January 25, 2026
**Maintained By:** FRANKENSTEIN Development Team
