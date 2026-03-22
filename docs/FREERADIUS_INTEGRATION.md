# FreeRADIUS Integration with RoXX MFA

## Overview

This guide explains how to integrate RoXX's MFA/2FA functionality with FreeRADIUS using the Python module (`rlm_python3`). This allows VPN users to authenticate with password+TOTP through FreeRADIUS.

## Architecture

```
VPN Client → FreeRADIUS Server → rlm_python3 → RoXX Backend → MFA Database
                                                    ↓
                                            LDAP/SQL/File Backend
```

**Flow:**
1. User enters `password+TOTP` in VPN client
2. FreeRADIUS receives Access-Request
3. `rlm_python3` module calls RoXX authentication
4. RoXX extracts TOTP, verifies it
5. RoXX authenticates base password against backend
6. Access-Accept or Access-Reject returned

## Prerequisites

### System Requirements

- **FreeRADIUS 3.0+** with `rlm_python3` module
- **Python 3.8+**
- **RoXX** installed and configured
- **SQLite** for MFA database (already included)

### Install FreeRADIUS with Python Support

#### Ubuntu/Debian

```bash
sudo apt-get update
sudo apt-get install freeradius freeradius-python3
```

#### CentOS/RHEL

```bash
sudo yum install freeradius freeradius-python3
```

##Installation

### Step 1: Copy FreeRADIUS Module

The module is already included at `roxx/integrations/freeradius_module.py`.

```bash
# Copy to FreeRADIUS mods-config
sudo cp roxx/integrations/freeradius_module.py \
        /etc/freeradius/3.0/mods-config/python3/roxx_auth.py

# Set permissions
sudo chown freerad:freerad /etc/freeradius/3.0/mods-config/python3/roxx_auth.py
sudo chmod 640 /etc/freeradius/3.0/mods-config/python3/roxx_auth.py
```

### Step 2: Configure Environment

Set ROXX_PATH for FreeRADIUS:

```bash
# Edit /etc/systemd/system/freeradius.service.d/roxx.conf
sudo mkdir -p /etc/systemd/system/freeradius.service.d
sudo tee /etc/systemd/system/freeradius.service.d/roxx.conf << EOF
[Service]
Environment="ROXX_PATH=/opt/RoXX"
EOF

# Reload systemd
sudo systemctl daemon-reload
```

### Step 3: Configure Python Module

Edit `/etc/freeradius/3.0/mods-available/python3`:

```
python3 {
    mod_instantiate = ${modconfdir}/${.:name}/roxx_auth
    func_instantiate = instantiate

    mod_authorize = ${modconfdir}/${.:name}/roxx_auth
    func_authorize = authorize

    mod_authenticate = ${modconfdir}/${.:name}/roxx_auth
    func_authenticate = authenticate

    mod_post_auth = ${modconfdir}/${.:name}/roxx_auth
    func_post_auth = post_auth
}
```

### Step 4: Enable Module

```bash
cd /etc/freeradius/3.0/mods-enabled
sudo ln -s ../mods-available/python3 python3
```

### Step 5: Configure Site

Edit `/etc/freeradius/3.0/sites-available/default`:

```
authorize {
    preprocess
    python3  # Add RoXX authorization
    pap
}

authenticate {
    python3  # RoXX authentication with MFA support
}

post-auth {
    python3  # Optional: MFA usage tracking
}
```

## Testing

### Test with radtest

```bash
# Without MFA
radtest john.doe MyPassword localhost 1812 testing123

# With MFA (password + TOTP)
radtest jane.smith SecurePass456789 localhost 1812 testing123
```

### Debug Mode

```bash
sudo freeradius -X

# Look for:
# [RoXX] Instantiating RoXX RADIUS module
# [RoXX] Loaded 3 RADIUS backends
# [RoXX] Authenticating user: john.doe
# [RoXX] TOTP verified for john.doe
# [RoXX] Authentication successful for john.doe
```

## Monitoring

### Logs

```bash
tail -f /var/log/freeradius/radius.log

# Sample:
# Info: [RoXX] Authenticating user: john.doe
# Info: [RoXX] TOTP verified for john.doe
# Info: [RoXX] Authentication successful for john.doe
# Auth: Login OK: [john.doe] (from client fortig ate port 0)
```

## See Also

- [MFA VPN Guide](MFA_VPN_GUIDE.md) - VPN client configuration
- [Deployment Guide](DEPLOYMENT_GUIDE.md) - Production setup
