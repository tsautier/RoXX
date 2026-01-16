# Changelog

All notable changes to RoXX will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [1.0.0-beta] - 2026-01-16

### Added

#### Core Features
- **Linux Only**: Optimized for Linux production environments (Debian/Ubuntu/RHEL)
- **Systemd Integration**: Native service management
- Interactive Console (`roxx-console`)
cture with modular design
- Rich TUI admin console with service management
- Interactive setup wizard for easy configuration
- Factory reset functionality

#### Authentication Modules
- inWebo Push authentication with HTTPS API
- TOTP (RFC 6238) with SHA1/SHA256/SHA512 support
- EntraID/Azure AD integration via MSAL
- Active Directory support (LDAP/Kerberos)
- Local users database
- YubiKey OTP validation

#### Web Interface
- Modern FastAPI-based admin panel
- TOTP QR code generation
- Responsive design with gradient UI
- RESTful API endpoints

#### Infrastructure
- Linux service management (systemd)
- Internationalization (EN/FR)
- PKI management (Local CA generation)
- Comprehensive logging with loguru

#### Testing & Quality
- 35+ unit tests with pytest
- Linux testing guide
- Code coverage reporting
- Type hints throughout

#### Documentation
- Comprehensive README
- Quick start guide
- FreeRADIUS integration guide
- Testing guide
- Build instructions
- Configuration templates

#### Packaging

- pip package configuration
- MANIFEST for distribution
- Requirements file

### Technical Details

- **Language**: Python 3.9+
- **Dependencies**: FastAPI, Rich, Questionary, httpx, cryptography, MSAL
- **Protocols**: RADIUS, EAP-PEAP, EAP-TTLS, EAP-TLS, MS-CHAPv2
- **Backends**: AD, LDAP, EntraID, Local, inWebo, YubiKey

---

## Future Releases

### Planned Features
- Dashboard with authentication statistics
- Advanced user management UI
- Certificate management interface
- RADIUS client configuration UI
- Real-time log viewer
- Multi-language support expansion

---

**RoXX** - Modern RADIUS Authentication Proxy
