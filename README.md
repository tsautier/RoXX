# RoXX (v1.0.0-beta8)

**Modern RADIUS proxy with integrated admin portal, multi-factor authentication, and enterprise identity provider support.**

![Version](https://img.shields.io/badge/version-1.0.0--beta8-blue)
![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

---

## 🚀 Features

### Core Functionality
- **RADIUS Proxy**: High-performance RADIUS authentication proxy
- **NPS Migration Assistant**: Import tools for effortless transition from Microsoft NPS
- **Multi-Backend Support**: LDAP, Active Directory, SAML 2.0 SSO, Entra ID
- **Admin Portal**: Modern web interface with real-time analytics
- **RESTful API**: Complete API for automation and integration

### Security & Authentication
- ✅ **Multi-Factor Authentication (MFA)**
  - TOTP/Authenticator Apps
  - WebAuthn (Security Keys, Biometrics)
  - TrustBuilder/inWebo Push Integration
  - SMS (via gateway integration)
- ✅ **SAML 2.0 Single Sign-On**
- ✅ **LDAP/Active Directory / Entra ID Integration**

### Management & Monitoring
- **Visual Dashboard**: Real-time authentication charts and health monitoring
- **Advanced Visibility**: Live log viewer with color-coded event tracking
- **User Management**: Create, edit, delete admin users
- **Audit Logs**: Complete system activity tracking
- **RBAC**: `superadmin`, `admin`, and `auditor` roles for portal access control

---

## 📋 Requirements

- **Python**: 3.8 or higher
- **Operating System**: Linux (Ubuntu/Debian recommended) or WSL2
- **Database**: SQLite (included)
- **Optional**: 
  - LDAP/AD server for directory integration
  - SAML IdP for SSO
  - SMS gateway for SMS MFA

---

## 🔧 Installation

### 1. Clone and Setup

```bash
git clone https://github.com/tsautier/RoXX.git
cd RoXX

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Initialize Database

```bash
python3 -m roxx.web.app
```

The admin portal will start on `http://localhost:8000`

**Default credentials:**
- Username: `admin`
- Password: `admin` (change immediately!)

### 3. Configuration

Configuration files are located in:
- **Linux**: `/etc/roxx/`
- **Development**: `~/.roxx/`

Key files:
- `roxx.db` - Main SQLite database
- `webauthn.db` - WebAuthn credentials
- `mfa.db` - MFA configuration

---

## 🎯 Quick Start

### Access the Admin Portal

1. Navigate to `http://localhost:8000`
2. Login with default credentials
3. **Change your password** under User Settings

### Understand Roles

RoXX uses three admin roles:
- `superadmin`
- `admin`
- `auditor`

See [docs/RBAC.md](docs/RBAC.md) for the complete permission matrix and role-management rules.

### Configure MFA

1. Go to **Settings → MFA Settings**
2. Choose your method:
   - **TOTP**: Scan QR code with authenticator app
   - **WebAuthn**: Register security key or biometric device
3. Complete setup and test login

### Add an Identity Provider

#### SAML 2.0

1. Go to **Config → Authentication Providers**
2. Click **+ Add Provider**
3. Select **SAML 2.0**
4. Fill in:
   - **Name**: e.g., "Corporate SSO"
   - **IdP Entity ID**: Your IdP's entity ID
   - **IdP SSO URL**: Your IdP's SSO endpoint
   - **IdP Certificate**: x509 certificate from IdP metadata
5. Configure your IdP with:
   - **Metadata URL**: `https://your-domain.com/auth/saml/metadata/{provider_id}`
   - **ACS URL**: `https://your-domain.com/auth/saml/acs/{provider_id}`

#### LDAP / Active Directory

1. Go to **Config → Authentication Providers**
2. Click **+ Add Provider**
3. Select **LDAP / Active Directory**
4. Configure:
   - **Server URL**: `ldap://dc.example.com:389`
   - **Base DN**: `dc=example,dc=com`
   - **Bind DN**: Service account DN
   - **Bind Password**: Service account password

---

## 📚 API Documentation

### Authentication

All API requests require authentication via session cookie or API token.

### Endpoints

#### User Management
```
GET    /api/admins              - List all admin users
POST   /api/admins              - Create new admin user
GET    /api/admins/{username}   - Get user details
PUT    /api/admins/{username}/role - Change user role
DELETE /api/admins/{username}   - Delete user
```

#### MFA Management
```
GET    /api/admins/{username}/mfa/status       - Get MFA status
GET    /api/admins/{username}/mfa/credentials  - List WebAuthn credentials
DELETE /api/admins/{username}/mfa/webauthn/{id} - Delete security key
POST   /api/admins/{username}/mfa/totp/reset   - Reset TOTP
```

#### Authentication Providers
```
GET    /api/auth-providers     - List providers
POST   /api/auth-providers     - Create provider
DELETE /api/auth-providers/{id} - Delete provider
```

### Example: Create Admin User

```bash
curl -X POST http://localhost:8000/api/admins \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john",
    "password": "SecurePass123!",
    "email": "john@example.com"
  }'
```

---

## 🔐 Security Best Practices

1. **Change Default Password**: Immediately change the default admin password
2. **Enable MFA**: Require MFA for all admin users
3. **Use HTTPS**: Deploy with proper SSL/TLS certificates
4. **Regular Updates**: Keep dependencies up to date
5. **Audit Logs**: Regularly review system audit logs
6. **API Tokens**: Use API tokens instead of passwords for automation
7. **Network Security**: Restrict admin portal access to trusted networks

---

## 🛠️ Configuration

### Environment Variables

```bash
# Application
ROXX_HOST=0.0.0.0
ROXX_PORT=8000
ROXX_DEBUG=false

# Database
ROXX_DB_PATH=/etc/roxx/roxx.db

# Security
ROXX_SECRET_KEY=your-secret-key-here
ROXX_SESSION_TIMEOUT=3600

# SAML
ROXX_SAML_SP_ENTITY_ID=https://your-domain.com
```

### SSL/TLS Configuration

Place certificates in `/etc/roxx/ssl/`:
- `cert.pem` - SSL certificate
- `key.pem` - Private key

The application will automatically use HTTPS if certificates are present.

---

## 📊 Monitoring

### System Health

Access the dashboard at `/dashboard` for:
- CPU utilization
- Memory usage
- Disk space
- Active sessions
- Recent authentication events

### Audit Logs

View comprehensive logs at `/logs`:
- User logins
- MFA events
- Configuration changes
- API requests
- SAML/LDAP authentication attempts

---

## 🐛 Troubleshooting

### Common Issues

**WebAuthn Not Working**
- Ensure using HTTPS or `localhost`
- Check browser compatibility (Chrome/Edge/Firefox/Safari recommended)
- Verify WebAuthn credentials in browser dev tools

**SAML Login Fails**
- Verify IdP certificate is correct
- Check SP Entity ID matches IdP configuration
- Review logs at `/config/auth-providers/logs`
- Ensure SP metadata uploaded to IdP

**LDAP Connection Issues**
- Verify network connectivity to LDAP server
- Check bind DN and password
- Test with `ldapsearch` command
- Review firewall rules

### Debug Mode

Enable debug logging:

```bash
export ROXX_DEBUG=true
python3 -m roxx.web.app
```

---

## 📖 Documentation

- **User Guide**: See `/docs/user-guide.md`
- **API Reference**: See `/docs/api-reference.md`
- **SAML Setup**: See `/docs/saml-setup.md`
- **LDAP/AD Setup**: See `/docs/ldap-setup.md`

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request


---

## 📝 License

## 📄 License

This project is licensed under the GNU Affero General Public License (AGPLv3) - see the [LICENSE](file:///c:/RoXX/LICENSE) file for details.

This license requires that users who interact with the software over a network must have access to the source code of the exact version they are using, including any modifications.

---

## 🙏 Acknowledgments

- **FastAPI** - Modern web framework
- **python3-saml** - SAML implementation
- **python-ldap** - LDAP integration
- **webauthn** - WebAuthn/FIDO2 support

---

## 📞 Support

For issues and questions:
- **GitHub Issues**: https://github.com/tsautier/RoXX/issues

---

**Built with ❤️ for secure, scalable authentication**

