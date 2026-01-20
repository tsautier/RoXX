# Palo Alto Networks VPN Integration Guide

## Overview

This guide explains how to integrate RoXX RADIUS authentication with Palo Alto Networks firewalls for GlobalProtect and IPsec VPN authentication.

## Architecture

```
VPN Client (GlobalProtect/IPsec)
    ↓
Palo Alto Firewall
    ↓ RADIUS Authentication
RoXX RADIUS Server
    ↓ User Lookup
LDAP/SQL/File Backend
```

## Prerequisites

- PAN-OS 9.0 or higher
- RoXX RADIUS server operational
- FreeRADIUS configured with RoXX module
- Network connectivity from Palo Alto to RoXX (UDP 1812/1813)
- Valid SSL certificate for GlobalProtect portal (if using GlobalProtect)

---

## Step 1: Configure RADIUS Client on RoXX

Add Palo Alto as a RADIUS client in `/etc/roxx/radius_clients.conf`:

```conf
# Palo Alto Firewall
client palo-alto-fw {
    ipaddr = 192.168.1.20
    secret = P@l0Alt0R@diusS3cr3t!2024
    shortname = palo-fw
    nas_type = other
}
```

---

## Step 2: Configure RADIUS Server Profile

### Via Web UI

1. Navigate to **Device > Server Profiles > RADIUS**
2. Click **Add**
3. Configure:
   - **Name:** `RoXX-RADIUS`
   - **Location:** `Shared` or specific `vsys`
4. Click **Add** under Servers:
   - **Name:** `RoXX-Primary`
   - **RADIUS Server:** `192.168.1.100` (RoXX server IP)
   - **Secret:** `P@l0Alt0R@diusS3cr3t!2024`
   - **Port:** `1812`
5. Click  **Advanced**:
   - **Timeout:** `5` seconds
   - **Retries:** `3`
6. Click **OK**

### Via CLI

```xml
set shared server-profile radius RoXX-RADIUS
set shared server-profile radius RoXX-RADIUS server RoXX-Primary ip-address 192.168.1.100
set shared server-profile radius RoXX-RADIUS server RoXX-Primary secret P@l0Alt0R@diusS3cr3t!2024
set shared server-profile radius RoXX-RADIUS server RoXX-Primary port 1812
set shared server-profile radius RoXX-RADIUS timeout 5
set shared server-profile radius RoXX-RADIUS retries 3
commit
```

---

## Step 3: Create Authentication Profile

### Via Web UI

1. Navigate to **Device > Authentication Profile**
2. Click **Add**
3. Configure:
   - **Name:** `VPN-Auth-Profile`
   - **Type:** `RADIUS`
   - **Server Profile:** Select `RoXX-RADIUS`
   - **Login:** Check `Allow`
   - **Retrieve user group:** Check (for group mapping)
   - **Username Modifier:** Optional (e.g., `%USERINPUT%` or `%USERINPUT%@domain.com`)
4. Click **OK**

### Via CLI

```xml
set shared authentication-profile VPN-Auth-Profile method radius
set shared authentication-profile VPN-Auth-Profile radius-server-profile RoXX-RADIUS
set shared authentication-profile VPN-Auth-Profile allow-list all
commit
```

---

## Step 4: GlobalProtect Configuration

### Portal Configuration

```xml
# Create GlobalProtect Portal
set network interface ethernet ethernet1/1 ip 203.0.113.10/24

set region Global
  
# Portal Configuration
set network globalprotect portal GP-Portal 
set network globalprotect portal GP-Portal server-certificate gp-portal-cert
set network globalprotect portal GP-Portal authentication-profile VPN-Auth-Profile
set network globalprotect portal GP-Portal ip-address 203.0.113.10

# Client Configuration
set network globalprotect portal GP-Portal client-config GP-Client
set network globalprotect portal GP-Portal client-config GP-Client gateways internal-gateway GP-Gateway
set network globalprotect portal GP-Portal client-config GP-Client tunnel-mode enable
set network globalprotect portal GP-Portal client-config GP-Client log-settings GP-Logs

commit
```

### Gateway Configuration

```xml
# Gateway Configuration
set network globalprotect gateway GP-Gateway
set network globalprotect gateway GP-Gateway server-certificate gp-gateway-cert
set network globalprotect gateway GP-Gateway authentication-profile VPN-Auth-Profile
set network globalprotect gateway GP-Gateway ip-address 203.0.113.10
set network globalprotect gateway GP-Gateway tunnel-mode enable

# Tunnel Interface
set network globalprotect gateway GP-Gateway tunnel-interface tunnel.10
set network interface tunnel units tunnel.10 ip 10.50.0.1/24
set zone VPN-Zone network layer3 tunnel.10

# Client Settings
set network globalprotect gateway GP-Gateway client-config GP-Config
set network globalprotect gateway GP-Gateway client-config GP-Config ip-pool GP-Pool
set network globalprotect gateway GP-Gateway client-config GP-Config dns primary 8.8.8.8
set network globalprotect gateway GP-Gateway client-config GP-Config dns secondary 8.8.4.4

# IP Pool
set network globalprotect gateway GP-Gateway  client-config GP-Config ip-pool GP-Pool ip-pool 10.50.0.10-10.50.0.250

commit
```

---

## Step 5: IPsec VPN Configuration (IKEv2)

### IKE Crypto Profile

```xml
set network ike crypto-profiles ike-crypto-profiles IKEv2-Crypto
set network ike crypto-profiles ike-crypto-profiles IKEv2-Crypto dh-group group14
set network ike crypto-profiles ike-crypto-profiles IKEv2-Crypto encryption aes-256-cbc
set network ike crypto-profiles ike-crypto-profiles IKEv2-Crypto authentication sha256
set network ike crypto-profiles ike-crypto-profiles IKEv2-Crypto lifetime hours 8
```

### IPsec Crypto Profile

```xml
set network ike crypto-profiles ipsec-crypto-profiles IPSec-Crypto
set network ike crypto-profiles ipsec-crypto-profiles IPSec-Crypto esp encryption aes-256-gcm
set network ike crypto-profiles ipsec-crypto-profiles IPSec-Crypto esp authentication none
set network ike crypto-profiles ipsec-crypto-profiles IPSec-Crypto lifetime hours 1
set network ike crypto-profiles ipsec-crypto-profiles IPSec-Crypto dh-group group14
```

### IKE Gateway with RADIUS Auth

```xml
set network ike gateway IKEv2-Gateway authentication type
set network ike gateway IKEv2-Gateway protocol ikev2 ike-crypto-profile IKEv2-Crypto
set network ike gateway IKEv2-Gateway protocol ikev2 dpd enable yes
set network ike gateway IKEv2-Gateway local-address ip 203.0.113.10
set network ike gateway IKEv2-Gateway local-address interface ethernet1/1
set network ike gateway IKEv2-Gateway authentication pre-shared-key key <PSK-Secret>
set network ike gateway IKEv2-Gateway peer-address dynamic
set network ike gateway IKEv2-Gateway auth-profile VPN-Auth-Profile
```

### IPsec Tunnel

```xml
set network tunnel ipsec IPSec-Tunnel auto-key ike-gateway IKEv2-Gateway
set network tunnel ipsec IPSec-Tunnel auto-key ipsec-crypto-profile IPSec-Crypto
set network tunnel ipsec IPSec-Tunnel tunnel-interface tunnel.20
set network tunnel ipsec IPSec-Tunnel anti-replay yes

set network interface tunnel units tunnel.20 ip 10.60.0.1/24
set zone IPSec-Zone network layer3 tunnel.20
```

---

## Step 6: Configure Security Policies

### GlobalProtect Policy

```xml
set rulebase security rules GP-to-Internal from VPN-Zone
set rulebase security rules GP-to-Internal to Trust
set rulebase security rules GP-to-Internal source any
set rulebase security rules GP-to-Internal destination any
set rulebase security rules GP-to-Internal application any
set rulebase security rules GP-to-Internal service any
set rulebase security rules GP-to-Internal action allow
set rulebase security rules GP-to-Internal log-end yes
```

### IPsec VPN Policy

```xml
set rulebase security rules IPSec-to-Internal from IPSec-Zone
set rulebase security rules IPSec-to-Internal to Trust
set rulebase security rules IPSec-to-Internal source any
set rulebase security rules IPSec-to-Internal destination any
set rulebase security rules IPSec-to-Internal application any
set rulebase security rules IPSec-to-Internal service any
set rulebase security rules IPSec-to-Internal action allow
set rulebase security rules IPSec-to-Internal log-end yes
```

---

## Step 7: Configure RoXX Backend

### LDAP Backend (Active Directory)

In RoXX Web UI (`/config/radius-backends`):

- **Backend Type:** LDAP
- **Name:** Corporate AD
- **Server:** `ldaps://dc.company.com:636`
- **Bind DN Format:** `cn={},ou=VPN Users,dc=company,dc=com`
- **Use TLS:** ☑️
- **Priority:** 10

---

## Step 8: User Group Mapping (Advanced)

### LDAP Group Mapping

Configure in FreeRADIUS for dynamic group assignment:

```conf
# Admin Users
DEFAULT Ldap-Group == "Domain Admins"
    Class := "admin",
    Reply-Message := "Admin Access Granted"

# Standard VPN Users
DEFAULT Ldap-Group == "VPN-Users"
    Class := "user",
    Reply-Message := "User Access Granted"
```

### Palo Alto Group Mapping

1. Navigate to **Device > User Identification > Group Mapping**
2. Add RADIUS server for group retrieval
3. Map RADIUS groups to Palo Alto security policies

---

## Verification

### Test RADIUS Authentication

From Palo Alto CLI:

```bash
test authentication authentication-profile VPN-Auth-Profile username testuser password testpass123
```

Expected output:
```
Authentication succeeded for user 'testuser'
+Primary authenticationsuccessful via RADIUS
```

### Debug RADIUS

```bash
# Enable RADIUS debug
debug radius on
debug radius detail

# Test authentication
test authentication authentication-profile VPN-Auth-Profile username testuser password testpass

# View logs
less mp-log rasmgr.log
```

### Check RoXX Logs

Navigate to `/config/radius-backends/logs` to see real-time authentication attempts with cache hit indicators.

---

## Troubleshooting

### Issue: "RADIUS server timeout"

**Solutions:**
1. Verify firewall allows UDP 1812/1813 from Palo Alto to RoXX
2. Check management interface routing
3. Verify RADIUS server IP is correct

```bash
# Test connectivity
ping source 192.168.1.20 host 192.168.1.100

# Test port
test radius-server name RoXX-RADIUS username test password test
```

### Issue: "Authentication failed"

**Debug Steps:**
1. Enable RADIUS debug: `debug radius on`
2. Check `/var/log/pan/rasmgr.log` on Palo Alto
3. Review RoXX logs at `/config/radius-backends/logs`
4. Verify shared secret matches exactly

### Issue: "User authenticated but no group membership"

**Solutions:**
1. Enable "Retrieve user group" in Authentication Profile
2. Configure LDAP group search in FreeRADIUS
3. Verify LDAP bind DN has permissions to read group membership

---

## RADIUS Attributes for Palo Alto

### Standard Attributes

```conf
# Assign static IP
Framed-IP-Address = 10.50.0.50

# Group membership
Class = "VPN-Users"

# Session timeout (seconds)
Session-Timeout = 28800

# Idle timeout
Idle-Timeout = 1800
```

### Palo Alto VSAs (Vendor-Specific Attributes)

```conf
# GlobalProtect specific
Palo-Alto-User-Group = "GP-VPN-Users"
Palo-Alto-User-Privilege = "normal"

# Portal assignment
Palo-Alto-Portal = "GP-Portal"
Palo-Alto-Gateway = "GP-Gateway"
```

---

## High Availability Configuration

### Dual RADIUS Servers

```xml
# Primary
set shared server-profile radius RoXX-RADIUS server RoXX-Primary ip-address 192.168.1.100

# Secondary/Failover
set shared server-profile radius RoXX-RADIUS server RoXX-Secondary ip-address 192.168.1.101
set shared server-profile radius RoXX-RADIUS server RoXX-Secondary secret P@l0Alt0R@diusS3cr3t!2024
set shared server-profile radius RoXX-RADIUS server RoXX-Secondary port 1812

commit
```

---

## Security Best Practices

1. **Certificate-Based Auth:** Use certificates for IKE gateway authentication instead of PSK when possible
2. **MFA Integration:** Combine RADIUS with MFA (TOTP/Duo) for additional security
3. **Session Limits:** Configure session timeout and idle timeout
4. **SSL/TLS:** Always use LDAPS (port 636) for backend LDAP connections
5. **Monitoring:** Enable logging for all VPN events and review regularly
6. **Network Segmentation:** Place RADIUS traffic on dedicated management network

---

## Performance Optimization

### RoXX Cache Configuration

```python
# roxx/core/radius_backends/cache.py
AuthCache(
    ttl=600,        # 10 minutes cache
    max_size=1000   # Support 1000 concurrent users
)
```

### Palo Alto Tuning

```xml
# Adjust RADIUS timeout for faster failover
set shared server-profile radius RoXX-RADIUS timeout 3
set shared server-profile radius RoXX-RADIUS retries 2
```

---

## Complete Working Example

### Scenario: GlobalProtect for 200 remote users

**Network:**
- Palo Alto: `203.0.113.10`
- RoXX RADIUS: `10.0.0.100`
- VPN IP Pool: `10.50.0.10 - 10.50.0.250`

**Configuration:**

```xml
# RADIUS Profile
set shared server-profile radius RoXX-RADIUS server RoXX-Primary ip-address 10.0.0.100
set shared server-profile radius RoXX-RADIUS server RoXX-Primary secret xK9mP2nQ7wR5tY8uI3oP
set shared authentication-profile VPN-Auth method radius radius-server-profile RoXX-RADIUS

# GlobalProtect Portal
set network globalprotect portal GP-Portal authentication-profile VPN-Auth
set network globalprotect portal GP-Portal server-certificate wildcard-cert
set network globalprotect portal GP-Portal ip-address 203.0.113.10

# Gateway
set network globalprotect gateway GP-GW authentication-profile VPN-Auth  
set network globalprotect gateway GP-GW tunnel-interface tunnel.10
set network globalprotect gateway GP-GW client-config GP-Config ip-pool 10.50.0.10-10.50.0.250
set network globalprotect gateway GP-GW client-config GP-Config dns primary 10.0.0.10

# Security Policy
set rulebase security rules GP-Access from VPN-Zone to Trust action allow
```

**Expected Performance:**
- Authentication: < 100ms
- Concurrent users: 200+
- Cache hit rate: 85%+

---

## Monitoring and Logs

### Palo Alto Logs

```bash
# View authentication logs
show log system subtype equal general

# Monitor active GlobalProtect sessions
show global-protect-gateway current-user

# RADIUS server status
show system radius-server all
```

### RoXX Logs

Access real-time logs at:
- Auth Provider Logs: `/config/auth-providers/logs`
- RADIUS Backend Logs: `/config/radius-backends/logs`

---

## Support

For issues or questions:
- RoXX Debug Logs: `/config/radius-backends/logs`
- Palo Alto Tech Docs: https://docs.paloaltonetworks.com
- GitHub Issues: https://github.com/tsautier/RoXX/issues
