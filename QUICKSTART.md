# RoXX Quick Start Guide

Get started with RoXX in minutes!

---

## 📦 Installation

### From Source

```bash
# Clone the repository
git clone https://github.com/yourusername/roxx.git
cd roxx

# Install dependencies
pip install -r requirements.txt

# Install RoXX
pip install -e .
```

### From PyPI (when available)

```bash
pip install roxx
```

---

## 🚀 First Steps

### 1. Launch Admin Console

```bash
roxx-console
```

Features:
- View service status
- Control services (start/stop/restart)
- System information
- Language selection (EN/FR)

### 2. Run Setup Wizard

```bash
roxx-setup
```

The wizard will guide you through:
- Language selection
- FreeRADIUS configuration
- Authentication provider setup
- PKI configuration
- Service configuration

### 3. Start Web Interface

```bash
roxx-web
```

Access at: http://localhost:8000

Features:
- TOTP enrollment with QR codes
- User management
- System monitoring

---

## 🔧 Configuration

### TOTP Setup

1. Run setup wizard: `roxx-setup`
2. Select TOTP as authentication method
3. Generate QR codes via web interface
4. Scan with Google/Microsoft Authenticator

### inWebo Push Setup

1. Obtain inWebo certificates and service ID
2. Run setup wizard
3. Configure certificates and API credentials
4. Test authentication

### EntraID Setup

1. Register app in Azure AD
2. Note Client ID and Tenant ID
3. Configure in setup wizard
4. Set environment variables for credentials

---

## 🧪 Testing

### Run Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=roxx

# Specific module
pytest tests/test_totp.py
```

### Test Installation

```bash
python test_installation.py
```

---

## 📚 Next Steps

- Read [TESTING_GUIDE.md](TESTING_GUIDE.md) for testing instructions
- See [FREERADIUS_INTEGRATION.md](FREERADIUS_INTEGRATION.md) for RADIUS setup
- Check [BUILD.md](BUILD.md) for packaging instructions
- Review configuration templates in `config/`

---

## 🆘 Common Issues

### Permission Denied

Run with administrator/sudo privileges:
```bash
sudo roxx-console
```

### Module Not Found

Ensure dependencies are installed:
```bash
pip install -r requirements.txt
```

### Port Already in Use (Web Interface)

Change the port in `roxx/web/app.py` or kill the process using port 8000.

---

**Happy authenticating with RoXX!** 🛡️
