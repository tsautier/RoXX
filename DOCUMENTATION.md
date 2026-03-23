# RoXX Documentation (GUI & CLI)

Welcome to RoXX (v1.0.0-beta7). This document outlines the available features and how to manage them via both the Web Interface (GUI) and the Command Line Interface (CLI).

---

## 🔐 1. Authentication Providers (LDAP, SAML, RADIUS)
RoXX acts as a proxy, fetching users from upstream sources.

### GUI Management
- Navigate to **Config > Auth Providers**.
- Add LDAP (AD), SAML, or RADIUS backends.
- Toggle "Enabled" to activate/deactivate a provider.

### CLI Management
```bash
roxx-console
# Follow Menu: [5] Configuration Management > [1] Manage Auth Providers
```

---

## 📡 2. RADIUS User Management (Local)
If you don't use an external IdP, you can manage users locally.

### GUI Management
- Navigate to **RADIUS Users** in the sidebar.
- Add/Delete users stored in `users.conf`.

### CLI Management
```bash
roxx-console
# Follow Menu: [1] User Management > [1] List RADIUS Users / [2] Add RADIUS User
```

---

## 📜 3. PKI & Certificate Management
Internal CA for 802.1X and SSL.

### GUI Management
- Navigate to **Security > PKI Management**.
- Initialize the internal CA if not present.
- Download the CA certificate for client distribution.

### CLI Management
```bash
roxx-console
# Follow Menu: [5] Configuration Management > [4] Manage PKI/Certs
```

---

## 🚀 4. NPS Migration Assistant
Easily transition from Windows NPS.

### GUI Management
- Navigate to **System > NPS Migration**.
- Upload your `nps_config.xml` (exported via `netsh nps export`).
- Preview and import the resulting configuration.

### CLI Management
```bash
# Direct command line import
python3 -m roxx.utils.nps_importer path/to/nps_config.xml
```

---

## ⚙️ 5. System Settings & Branding
Server name, ports, and logging.

### GUI Management
- Navigate to **Config > System Settings**.
- Modify Server Name, RADIUS Ports, and Log Levels.

### CLI Management
```bash
# Manual config edit
nano ~/.roxx/auth_providers.db (SQLite)
# Or use roxx-console settings
```

---

## 📊 6. Audit & Visibility
Track every authentication attempt.

### GUI Management
- View the **Dashboard** for charts.
- Navigate to **Audit Logs** for detailed history (with success/failure colors).

### CLI Management
```bash
roxx-console

---

## 🛠️ 7. Service Management (systemctl)
Manage RoXX services using standard Linux systemd commands.

### Deployment & Startup
1. **Install Service File**:
   ```bash
   sudo cp scripts/systemd/roxx-web.service /etc/systemd/system/
   sudo systemctl daemon-reload
   ```

2. **Enable & Start**:
   ```bash
   sudo systemctl enable roxx-web
   sudo systemctl start roxx-web
   ```

3. **Check Status**:
   ```bash
   sudo systemctl status roxx-web
   ```

4. **View Logs**:
   ```bash
   sudo journalctl -u roxx-web -f
   ```
