# Fortinet FortiGate VPN Integration Guide

## Overview

This guide explains how to integrate RoXX RADIUS authentication with Fortinet FortiGate firewalls for IKEv2 VPN authentication.

## Architecture

```
VPN Client (IKEv2)
    ↓
FortiGate Firewall
    ↓ RADIUS Authentication
RoXX RADIUS Server
    ↓ User Lookup
LDAP/SQL/File Backend
```

## Prerequisites

- FortiGate firmware 6.0 or higher
- RoXX RADIUS server operational
- FreeRADIUS configured with RoXX module
- Network connectivity from FortiGate to RoXX (UDP 1812/1813)

---

## Step 1: Configure RADIUS Client on RoXX

Add FortiGate as a RADIUS client in `/etc/roxx/radius_clients.conf`:

```conf
# FortiGate VPN Gateway
client fortigate-vpn {
    ipaddr = 192.168.1.10
    secret = Y0urStr0ngR@diusSecret123
    shortname = fortigate-fw
    nas_type = other
}
```

**Important:** Replace `192.168.1.10` with your FortiGate's management IP and use a strong shared secret.

---

## Step 2: Configure RADIUS Server on FortiGate

### CLI Configuration

```bash
config user radius
    edit "RoXX-RADIUS"
        set server "192.168.1.100"
        set secret "Y0urStr0ngR@diusSecret123"
        set timeout 5
        set all-usergroup disable
        set auth-type auto
        set source-ip 192.168.1.10
    next
end
```

### GUI Configuration

1. Navigate to **User & Authentication > RADIUS Servers**
2. Click **Create New**
3. Configure:
   - **Name:** `RoXX-RADIUS`
   - **Primary Server IP:** `192.168.1.100` (RoXX server IP)
   - **Secondary Server:** (optional, for redundancy)
   - **Authentication Method:** `Auto`
   - **Shared Secret:** `Y0urStr0ngR@diusSecret123`
   - **Timeout:** `5` seconds
   - **Source IP:** Your FortiGate's interface IP
4. Click **Test Connectivity** to verify
5. Click **OK**

---

## Step 3: Create User Group

```bash
config user group
    edit "VPN-Users"
        set member "RoXX-RADIUS"
    next
end
```

Or via GUI:
1. **User & Authentication > User Groups**
2. **Create New**
3. **Name:** `VPN-Users`
4. **Type:** `Firewall`
5. **Remote Groups:** Add `RoXX-RADIUS`

---

## Step 4: Configure IKEv2 VPN

### Phase 1 (IKE Gateway)

```bash
config vpn ipsec phase1-interface
    edit "IKEv2-VPN"
        set type dynamic
        set interface "wan1"
        set ike-version 2
        set peertype any
        set net-device disable
        set mode-cfg enable
        set proposal aes256-sha256
        set dhgrp 14
        set wizard-type dialup-forticlient
        set xauthtype auto
        set authmethod signature
        set mode main
        set psksecret <VPN-PSK-Secret>
        set dpd on-idle
        set dpd-retryinterval 5
    next
end
```

### Phase 2 (IPsec Tunnel)

```bash
config vpn ipsec phase2-interface
    edit "IKEv2-VPN-P2"
        set phase1name "IKEv2-VPN"
        set proposal aes256-sha256
        set dhgrp 14
        set auto-negotiate enable
    next
end
```

### Assign IP Pool

```bash
config firewall address
    edit "VPN-Pool"
        set type iprange
        set start-ip 10.10.10.10
        set end-ip 10.10.10.100
    next
end

config vpn ipsec phase1-interface
    edit "IKEv2-VPN"
        set ipv4-start-ip 10.10.10.10
        set ipv4-end-ip 10.10.10.100
        set ipv4-netmask 255.255.255.0
    next
end
```

---

## Step 5: Configure Authentication

### Link RADIUS to VPN

```bash
config vpn ipsec phase1-interface
    edit "IKEv2-VPN"
        set authmethod signature
        set xauthtype auto
        set mode-cfg enable
        set assign-ip enable
        set assign-ip-from name
        set ipv4-dns-server1 8.8.8.8
        set ipv4-dns-server2 8.8.4.4
        set usrgrp "VPN-Users"
    next
end
```

### Firewall Policy

```bash
config firewall policy
    edit 0
        set name "VPN-to-LAN"
        set srcintf "IKEv2-VPN"
        set dstintf "internal"
        set srcaddr "all"
        set dstaddr "all"
        set action accept
        set schedule "always"
        set service "ALL"
        set groups "VPN-Users"
        set nat enable
    next
end
```

---

## Step 6: Configure RoXX Backend

Choose one of the following backends:

### LDAP Backend (Active Directory)

In RoXX Web UI (`/config/radius-backends`):

- **Backend Type:** LDAP
- **Name:** Corporate AD
- **Server:** `ldap://dc.company.com:389`
- **Bind DN Format:** `cn={},ou=VPN Users,dc=company,dc=com`
- **Use TLS:** ☑️ (Recommended)
- **Priority:** 10

### SQL Backend (MySQL/PostgreSQL)

```sql
CREATE TABLE radius_users (
    username VARCHAR(64) PRIMARY KEY,
    password VARCHAR(255) NOT NULL,  -- BCrypt hash
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO radius_users (username, password) 
VALUES ('vpnuser', '$2b$12$...');  -- BCrypt hash
```

In RoXX Web UI:
- **Backend Type:** SQL
- **DB Type:** MySQL
- **Host:** `localhost`
- **Database:** `radius`
- **Password Type:** BCrypt

---

## Step 7: RADIUS Attributes (Advanced)

### Group-Based Access Control

Configure in FreeRADIUS `/etc/freeradius/users`:

```conf
# VPN Admins - Full access
DEFAULT Ldap-Group == "VPN-Admins"
    Framed-IP-Address = 10.10.10.5,
    Class = "admin-access"

# VPN Users - Restricted
DEFAULT Ldap-Group == "VPN-Users"
    Framed-IP-Address = 10.10.10.0/24,
    Class = "user-access"
```

### FortiGate RADIUS VSAs

```conf
Fortinet-Group-Name = "VPN-Users"
Fortinet-Vdom-Name = "root"
```

---

## Verification

### Test RADIUS Authentication

From FortiGate CLI:

```bash
diagnose test authserver radius RoXX-RADIUS testuser testpassword
```

Expected output:
```
authenticate 'testuser': succeeded
```

### Debug RADIUS on FortiGate

```bash
diagnose debug application radiusd -1
diagnose debug enable
```

### Check RoXX Logs

Navigate to `/config/radius-backends/logs` in RoXX Web UI to see real-time authentication attempts.

---

## Troubleshooting

### Issue: "RADIUS server not responding"

**Solutions:**
1. Verify firewall rules allow UDP 1812/1813
2. Check RADIUS client IP matches FortiGate's source interface
3. Verify shared secret matches on both sides

```bash
# FortiGate: Check connectivity
execute ping 192.168.1.100

# Check RADIUS ports
execute telnet 192.168.1.100 1812
```

### Issue: "Authentication failed"

**Solutions:**
1. Verify user exists in RoXX backend
2. Check username format (use SAMAccountName for AD)
3. Review RoXX debug logs at `/config/radius-backends/logs`
4. Test backend connection in RoXX UI

### Issue: "User authenticated but no IP assigned"

**Solutions:**
1. Verify IP pool configuration in phase1
2. Check `mode-cfg enable` is set
3. Ensure `assign-ip enable` is configured

---

## Security Best Practices

1. **Use TLS for LDAP:** Always enable TLS when connecting to LDAP servers
2. **Strong Shared Secrets:** Use 20+ character random secrets
3. **Network Segmentation:** Isolate RADIUS traffic on management VLAN
4. **Certificate Validation:** Use certificate-based authentication when possible
5. **Log Monitoring:** Regularly review authentication logs in RoXX
6. **MFA Integration:** Consider adding TOTP/OTP for additional security

---

## Performance Tuning

### RoXX Cache Settings

In `roxx/core/radius_backends/cache.py`:

```python
# Increase cache TTL for better performance
AuthCache(ttl=600)  # 10 minutes

# Increase cache size for high-traffic environments
AuthCache(max_size=1000)  # 1000 entries
```

### FortiGate Optimizations

```bash
config user radius
    edit "RoXX-RADIUS"
        set timeout 3
        set nas-ip <fortigate-ip>
    next
end
```

---

## Complete Working Example

### Scenario: 100 remote workers, Active Directory backend

**RoXX Backend Configuration:**
- LDAP: `ldaps://dc.company.com:636`
- Bind DN: `cn={},ou=VPN Users,dc=company,dc=com`
- Cache: 5min TTL, 250 entries

**FortiGate Configuration:**
```bash
# RADIUS Server
config user radius
    edit "RoXX-RADIUS"
        set server "10.0.0.100"
        set secret "xK9mP2nQ7wR5tY8uI3oP6aS4dF1gH0jL"
        set timeout 5
    next
end

# User Group
config user group
    edit "VPN-Users"
        set member "RoXX-RADIUS"
    next
end

# IKEv2 VPN
config vpn ipsec phase1-interface
    edit "Corporate-VPN"
        set type dynamic
        set interface "wan1"
        set ike-version 2
        set peertype any
        set proposal aes256gcm-prfsha384
        set dhgrp 21
        set xauthtype auto
        set mode-cfg enable
        set ipv4-start-ip 10.20.0.10
        set ipv4-end-ip 10.20.0.250
        set ipv4-netmask 255.255.255.0
        set ipv4-dns-server1 10.0.0.10
        set usrgrp "VPN-Users"
    next
end
```

**Expected Performance:**
- Authentication latency: < 50ms (with cache hit)
- Throughput: 250+ auth/sec
- Cache hit rate: 80-90%

---

## Support

For issues or questions:
- RoXX Debug Logs: `/config/radius-backends/logs`
- FortiGate RADIUS debug: `diagnose debug application radiusd -1`
- GitHub Issues: https://github.com/tsautier/RoXX/issues
