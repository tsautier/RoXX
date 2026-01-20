# RoXX Linux Testing Guide

This guide provides testing procedures for RoXX on Linux production environments.

## 🐧 Linux Testing

### 1. Initial Setup
```bash
# Install package
pip install -e .

# Run setup
sudo python -m roxx.cli.setup
```
- ✅ Detects OS as "Linux"
- ✅ Configuration path: `/etc/roxx`

### 2. Service Verification
```bash
# Check service status via console
sudo python -m roxx.cli.console
# Menu -> Services Status
```
- ✅ Should detect `freeradius` status correctly via systemctl

### 3. Authentication Tests
Use the included `test_roxx.py` script:
```bash
python test_roxx.py
```

### 4. Unit Tests
Run the full test suite:
```bash
pytest
```

## ✅ Acceptance Criteria
- [x] Console launches on Linux
- [x] Setup wizard completes successfully
- [x] Systemd services detected correctly
- [x] Auth modules function (inWebo, TOTP)
- [x] Unit tests pass

## 📞 Support
Logs are located at: `/var/log/roxx/`
