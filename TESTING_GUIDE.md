# RoXX Multi-OS Testing Guide

## 🧪 Complete Testing Checklist

This guide provides step-by-step testing procedures for RoXX on Windows, Linux, and macOS.

---

## 📋 Pre-Test Checklist

- [ ] Python 3.9+ installed
- [ ] Administrator/sudo privileges
- [ ] Dependencies installed: `pip install -r requirements.txt`
- [ ] FreeRADIUS installed (for full testing)

---

## 🪟 Windows Testing

### Environment Setup

```powershell
# Check Python version
python --version  # Should be 3.9+

# Install dependencies
pip install -r requirements.txt

# Verify installation
python test_installation.py
```

### Test 1: Console Launch

```powershell
# Run as Administrator (Right-click PowerShell → Run as administrator)
cd C:\RoXX
python -m roxx
```

**Expected**:
- ✅ Console loads with Rich TUI
- ✅ Shows "RoXX Admin Console v1.0-beta"
- ✅ Detects OS as "Windows"
- ✅ Menu displays with icons

**Test Actions**:
1. Navigate to "📊 Services Status"
2. Check service detection (may show UNKNOWN on Windows without FreeRADIUS)
3. Navigate to "💻 System Information"
4. Verify CPU, RAM, Disk info displayed
5. Test "🌐 Change Language" (EN ↔ FR)
6. Exit gracefully

### Test 2: Setup Assistant

```powershell
python -m roxx.cli.setup
```

**Expected**:
- ✅ Welcome screen displays
- ✅ Language selection works
- ✅ Configuration wizard runs
- ✅ Creates config files in `C:\ProgramData\RoXX\`

**Test Actions**:
1. Select language (EN or FR)
2. Configure at least one auth provider (TOTP recommended)
3. Skip PKI or create local CA
4. Verify config file created: `C:\ProgramData\RoXX\roxx_config.json`

### Test 3: Authentication Modules

**TOTP Test**:
```powershell
# Set environment variables
$env:USER_NAME = "testuser"
$env:USER_PASSWORD = "123456"

# Run TOTP module
python -m roxx.core.auth.totp
```

**Expected**: Exit code 1 (no secret configured) or 0 (if secret exists)

**inWebo Test** (requires certificates):
```powershell
$env:USER_NAME = "john.doe"
$env:INWEBO_SERVICE_ID = "10408"

python -m roxx.core.auth.inwebo
```

### Test 4: Unit Tests

```powershell
# Run all tests
pytest

# Run with coverage
pytest --cov=roxx --cov-report=html

# Open coverage report
start htmlcov\index.html
```

**Expected**: All tests pass (35+ tests)

### Test 5: Package Building

```powershell
# Install PyInstaller
pip install pyinstaller

# Build Windows executable
pyinstaller roxx.spec

# Test executable
.\dist\roxx.exe
```

**Expected**: Standalone exe runs without Python installed

---

## 🐧 Linux Testing

### Environment Setup

```bash
# Check Python version
python3 --version  # Should be 3.9+

# Install dependencies
pip3 install -r requirements.txt

# Install FreeRADIUS (optional but recommended)
sudo apt-get install freeradius  # Debian/Ubuntu
# or
sudo yum install freeradius  # RHEL/CentOS
```

### Test 1: Console Launch

```bash
# Run with sudo
cd /path/to/RoXX
sudo python3 -m roxx
```

**Expected**:
- ✅ Console loads with Rich TUI
- ✅ Detects OS as "Linux"
- ✅ Service detection works (systemctl)

**Test Actions**:
1. Check "📊 Services Status"
   - Should show FreeRADIUS status (if installed)
   - May show winbind, smbd, nmbd as STOPPED
2. Try "🎮 Control Services"
   - Test start/stop/restart FreeRADIUS
3. Verify "💻 System Information"

### Test 2: Setup Assistant

```bash
sudo python3 -m roxx.cli.setup
```

**Expected**:
- ✅ Detects FreeRADIUS in `/etc/freeradius/3.0` or `/etc/freeradius`
- ✅ Creates config in `/usr/local/etc/`

**Test Actions**:
1. Configure Active Directory (if available)
2. Configure LDAP (if available)
3. Configure inWebo with certificates
4. Create local CA for PKI

### Test 3: Service Management

```bash
# Test service detection
sudo python3 -c "from roxx.core.services import ServiceManager; mgr = ServiceManager(); print(mgr.get_all_services_status())"

# Test service control
sudo python3 -c "from roxx.core.services import ServiceManager; mgr = ServiceManager(); print('Start:', mgr.start('freeradius'))"
```

**Expected**: Services detected and controlled via systemctl

### Test 4: FreeRADIUS Integration

```bash
# Configure FreeRADIUS to use RoXX modules
sudo nano /etc/freeradius/3.0/mods-enabled/exec

# Add:
# exec roxx_inwebo {
#     wait = yes
#     program = "python3 -m roxx.core.auth.inwebo"
#     input_pairs = request
# }

# Test FreeRADIUS config
sudo freeradius -X

# Test RADIUS authentication
echo "User-Name = testuser, User-Password = testpass" | radclient -x localhost:1812 auth testing123
```

### Test 5: Unit Tests

```bash
pytest
pytest --cov=roxx --cov-report=term-missing
```

---

## 🍎 macOS Testing

### Environment Setup

```bash
# Install Python 3.9+ (via Homebrew)
brew install python@3.9

# Install dependencies
pip3 install -r requirements.txt

# Install FreeRADIUS (optional)
brew install freeradius-server
```

### Test 1: Console Launch

```bash
sudo python3 -m roxx
```

**Expected**:
- ✅ Detects OS as "Darwin"
- ✅ Service detection uses launchctl

### Test 2: Service Detection

```bash
# macOS uses launchctl instead of systemctl
sudo python3 -c "from roxx.core.services import ServiceManager; mgr = ServiceManager(); print(mgr.os_type); print(mgr.get_all_services_status())"
```

**Expected**: Detects services via `launchctl list`

### Test 3: Path Detection

```bash
python3 -c "from roxx.utils.system import SystemManager; print('Config:', SystemManager.get_config_dir()); print('Data:', SystemManager.get_data_dir())"
```

**Expected**:
- Config: `/usr/local/etc`
- Data: `/usr/local/var`

---

## 🔄 Cross-Platform Tests

### Test 1: Multi-OS Compatibility

Run on all three platforms:

```bash
python3 test_roxx.py
```

**Expected**: All tests pass on all platforms

### Test 2: Path Handling

```python
from roxx.utils.system import SystemManager
from pathlib import Path

# Test path creation
config_dir = SystemManager.get_config_dir()
test_file = config_dir / "test.txt"

# Should work on all OS
print(f"Config dir: {config_dir}")
print(f"Exists: {config_dir.exists()}")
```

### Test 3: Command Execution

```python
from roxx.utils.system import SystemManager

# Test OS-appropriate commands
if SystemManager.get_os() == 'windows':
    result = SystemManager.run_command(['cmd', '/c', 'echo', 'test'])
else:
    result = SystemManager.run_command(['echo', 'test'])

print(f"Output: {result.stdout}")
print(f"Success: {result.returncode == 0}")
```

---

## 📊 Test Results Template

| Test | Windows | Linux | macOS | Notes |
|------|---------|-------|-------|-------|
| Console Launch | ⬜ | ⬜ | ⬜ | |
| Setup Wizard | ⬜ | ⬜ | ⬜ | |
| Service Detection | ⬜ | ⬜ | ⬜ | |
| TOTP Auth | ⬜ | ⬜ | ⬜ | |
| inWebo Auth | ⬜ | ⬜ | ⬜ | |
| Unit Tests | ⬜ | ⬜ | ⬜ | |
| Package Build | ⬜ | ⬜ | ⬜ | |

**Legend**: ✅ Pass | ❌ Fail | ⚠️ Partial | ⬜ Not Tested

---

## 🐛 Common Issues & Solutions

### Issue 1: "Module not found"

**Solution**:
```bash
# Ensure you're in the RoXX directory
cd /path/to/RoXX

# Or install as package
pip install -e .
```

### Issue 2: "Permission denied"

**Solution**:
- Windows: Run PowerShell as Administrator
- Linux/macOS: Use `sudo`

### Issue 3: "Service not found"

**Solution**:
- Install FreeRADIUS first
- Or test with other services (smbd, nmbd on Linux)

### Issue 4: Rich/Questionary not displaying correctly

**Solution**:
```bash
# Update terminal
# Windows: Use Windows Terminal instead of cmd.exe
# Linux: Ensure UTF-8 locale
export LANG=en_US.UTF-8
```

---

## ✅ Acceptance Criteria

RoXX is considered **fully tested** when:

- [x] Console launches on all 3 OS
- [x] Setup wizard completes on all 3 OS
- [x] Service detection works on all 3 OS
- [x] At least one auth module tested on each OS
- [x] All unit tests pass on all 3 OS
- [x] Package builds successfully on all 3 OS
- [x] No critical bugs found
- [x] Documentation is accurate

---

## 📝 Test Report Template

```markdown
# RoXX Test Report

**Date**: YYYY-MM-DD
**Tester**: [Name]
**Version**: 1.0-beta

## Environment
- OS: [Windows 10/11 | Ubuntu 22.04 | macOS 13+]
- Python: [Version]
- FreeRADIUS: [Version or N/A]

## Test Results
[Use table above]

## Issues Found
1. [Issue description]
   - Severity: [Critical | High | Medium | Low]
   - Steps to reproduce: [...]
   - Expected: [...]
   - Actual: [...]

## Conclusion
[Pass | Fail | Conditional Pass]

## Recommendations
[Any suggestions for improvement]
```

---

## 🚀 Automated Testing (Future)

### GitHub Actions Example

```yaml
name: Multi-OS Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        python-version: ['3.9', '3.10', '3.11', '3.12']
    
    steps:
    - uses: actions/checkout@v3
    - uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    - run: pip install -r requirements.txt
    - run: pip install pytest pytest-cov
    - run: pytest --cov=roxx
```

---

## 📞 Support

If you encounter issues during testing:

1. Check the logs in the appropriate directory:
   - Windows: `C:\ProgramData\RoXX\logs\`
   - Linux/macOS: `/usr/local/var/log/roxx/`

2. Run with debug mode:
   ```bash
   python -m roxx --debug
   ```

3. Report issues with:
   - OS and version
   - Python version
   - Full error message
   - Steps to reproduce
