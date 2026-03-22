# Stormshield Network Security VPN Integration Guide

## Overview

This guide explains how to integrate RoXX RADIUS authentication with Stormshield Network Security (SNS) firewalls for IPsec VPN authentication.

## Architecture

```
VPN Client (IPsec/IKEv2/L2TP)
    ↓
Stormshield Firewall
    ↓ RADIUS Authentication
RoXX RADIUS Server
    ↓ User Lookup
LDAP/SQL/File Backend
```

## Prerequisites

- Stormshield SNS firmware 3.7 or higher
- RoXX RADIUS server operational
- FreeRADIUS configured with RoXX module
- Network connectivity from Stormshield to RoXX (UDP 1812/1813)
- Valid SSL certificates for SSL-VPN (if using SSL-VPN)

---

## Step 1: Configure RADIUS Client on RoXX

Add Stormshield as a RADIUS client in `/etc/roxx/radius_clients.conf`:

```conf
# Stormshield Firewall
client stormshield-fw {
    ipaddr = 192.168.1.30
    secret = St0rmSh13ldR@dius!2024Secr3t
    shortname = sns-fw
    nas_type = other
}
```

---

## Step 2: Configure RADIUS Server on Stormshield

### Via Web Administration

1. Navigate to **Configuration > Users > RADIUS servers**
2. Click **Add**
3. Configure RADIUS server:
   - **Name:** `RoXX-RADIUS`
   - **Server IP address:** `192.168.1.100`
   - **Authentication port:** `1812`
   - **Accounting port:** `1813`
   - **Shared secret:** `St0rmSh13ldR@dius!2024Secr3t`
   - **Timeout:** `5` seconds
   - **Number of retries:** `3`
   - **Authentication protocol:** `PAP` or `CHAP`
4. Click **Test** to verify connectivity
5. Click **Apply**

### Via CLI

```bash
# Add RADIUS server
RADIUS SERVER ADD NAME="RoXX-RADIUS" IPADDR="192.168.1.100" SECRET="St0rmSh13ldR@dius!2024Secr3t" AUTHPORT=1812 ACCTPORT=1813 TIMEOUT=5 RETRY=3

# Enable RADIUS authentication
CONFIG USER LDAPAUTH SETPARAM RADIUS ENABLE=1

# Save configuration
CONFIG ACTIVATE
```

---

## Step 3: Configure Authentication Policy

### Create Authentication Policy

1. Navigate to **Configuration > Users > Authentication**
2. Click **Add authentication policy**
3. Configure:
   - **Name:** `VPN-RADIUS-Auth`
   - **Type:** `RADIUS`
   - **RADIUS server:** Select `RoXX-RADIUS`
   - **Fallback:** Optional local database
   - **Enable user group retrieval:** ☑️
4. Click **Apply**

### CLI Configuration

```bash
# Create authentication policy
CONFIG POLICY AUTH ADD NAME="VPN-RADIUS-Auth" TYPE=RADIUS SERVER="RoXX-RADIUS" FALLBACK=LOCAL

# Apply policy to VPN
CONFIG VPN IPSEC SETPARAM AUTHPOLICY="VPN-RADIUS-Auth"

CONFIG ACTIVATE
```

---

## Step 4: IPsec VPN Configuration

### IKEv2 VPN Gateway

1. Navigate to **Configuration > VPN > IPsec tunnels**
2. Click **Add** > **Mobile users**
3. Configure **General settings**:
   - **Gateway ID:** `vpn.company.com`
   - **Pre-shared key:** (Strong PSK)
   - **IKE version:** `IKEv2 only`
   - **Authentication method:** `Pre-shared key + XAuth`

4. Configure **Phase 1 (IKE)**:
   - **Encryption:** `AES-256`
   - **Integrity:** `SHA-256`
   - **DH Group:** `Group 14 (2048-bit)`
   - **Lifetime:** `28800` seconds

5. Configure **Phase 2 (IPsec)**:
   - **Encryption:** `AES-256-GCM`
   - **Integrity:** `None` (GCM includes integrity)
   - **PFS Group:** `Group 14`
   - **Lifetime:** `3600` seconds

6. **Authentication settings**:
   - **Authentication policy:** `VPN-RADIUS-Auth`
   - **XAuth:** Enable
   - **User group:** Create or select group

7. **Address assignment**:
   - **IP pool:** `10.70.0.10 - 10.70.0.250`
   - **DNS servers:** `10.0.0.10, 8.8.8.8`
   - **DNS domain:** `vpn.company.local`

8. Click **Apply**

### CLI Configuration

```bash
# Create IPsec VPN for mobile users
CONFIG VPN IPSEC MOBILE ADD NAME="Corporate-VPN" \
  GATEWAY="vpn.company.com" \
  PSK="YourStrongPSK" \
  IKEVERSION=2 \
  IKEENCRYPTION=AES256 \
  IKEHASH=SHA256 \
  IKEDH=14 \
  IKELIFETIME=28800 \
  IPSECENCRYPTION=AES256GCM \
  IPSECDH=14 \
  IPSECLIFETIME=3600 \
  AUTHPOLICY="VPN-RADIUS-Auth" \
  XAUTH=ENABLE \
  IPPOOL="10.70.0.10-10.70.0.250" \
  DNS1="10.0.0.10" \
  DNS2="8.8.8.8"

CONFIG ACTIVATE
```

---

## Step 5: SSL-VPN Configuration (Web Portal)

### Enable SSL-VPN Portal

1. Navigate to **Configuration > VPN > SSL-VPN**
2. Click **Enable SSL-VPN**
3. Configure:
   - **Portal URL:** `https://vpn.company.com:443`
   - **SSL certificate:** Upload or select valid certificate
   - **Authentication:** Select `VPN-RADIUS-Auth`
   - **Session timeout:** `28800` seconds
   - **Idle timeout:** `1800` seconds

4. **Network settings**:
   - **Virtual IP pool:** `10.80.0.10 - 10.80.0.100`
   - **DNS servers:** `10.0.0.10, 8.8.8.8`
   - **Split tunneling:** Configure routes

5. Click **Apply**

### CLI Configuration

```bash
# Enable and configure SSL-VPN
CONFIG VPN SSL SETPARAM ENABLE=1 \
  URL="https://vpn.company.com:443" \
  CERT="vpn-cert" \
  AUTHPOLICY="VPN-RADIUS-Auth" \
  SESSIONTIMEOUT=28800 \
  IDLETIMEOUT=1800 \
  IPPOOL="10.80.0.10-10.80.0.100" \
  DNS1="10.0.0.10" \
  DNS2="8.8.8.8"

CONFIG ACTIVATE
```

---

## Step 6: L2TP/IPsec Configuration

### Configure L2TP Server

1. Navigate to **Configuration > VPN > L2TP**
2. Enable L2TP server
3. Configure:
   - **Authentication:** `VPN-RADIUS-Auth`
   - **IPsec encapsulation:** Enable
   - **Pre-shared key:** (Strong PSK)
   - **IP address pool:** `10.90.0.10 - 10.90.0.100`
   - **DNS servers:** `10.0.0.10, 8.8.8.8`

### CLI Configuration

```bash
CONFIG VPN L2TP SETPARAM ENABLE=1 \
  AUTHPOLICY="VPN-RADIUS-Auth" \
  IPSEC=ENABLE \
  PSK="L2tpPskSecret123" \
  IPPOOL="10.90.0.10-10.90.0.100" \
  DNS1="10.0.0.10" \
  DNS2="8.8.8.8"

CONFIG ACTIVATE
```

---

## Step 7: Firewall Rules

### Create VPN Access Rule

1. Navigate to **Configuration > Security policies > Filter rules**
2. Click **Add rule**
3. Configure:
   - **Name:** `VPN-to-LAN`
   - **Source:** `VPN networks` (10.70.0.0/24, 10.80.0.0/24, 10.90.0.0/24)
   - **Destination:** `Internal network`
   - **Services:** `Any` or specific services
   - **Action:** `PASS`
   - **Logging:** `Connections`
   - **Authentication:** Optional additional auth

4. Click **Apply**

### CLI Rule Configuration

```bash
# Add firewall rule for VPN traffic
CONFIG FILTER ADDRULE BEFORE=1 \
  NAME="VPN-to-LAN" \
  STATE=ON \
  SRCIF="VPN" \
  SRC="10.70.0.0/24,10.80.0.0/24,10.90.0.0/24" \
  DSTIF="Internal" \
  DST="192.168.0.0/16" \
  SERVICE="Any" \
  ACTION=PASS \
  LOG=CONNECTION

CONFIG ACTIVATE
```

---

## Step 8: Configure RoXX Backend

### LDAP Backend

In RoXX Web UI (`/config/radius-backends`):

- **Backend Type:** LDAP
- **Name:** Corporate LDAP
- **Server:** `ldaps://ldap.company.com:636`
- **Bind DN Format:** `uid={},ou=VPN Users,dc=company,dc=com`
- **Use TLS:** ☑️
- **Search Base:** `ou=VPN Users,dc=company,dc=com`
- **Priority:** 10

### Test Backend

Use the "Test Backend" feature in RoXX:
- **Test Username:** `vpnuser`
- **Test Password:** `TestPass123!`
- Click **Test Connection**

---

## Step 9: User Group Mapping

### LDAP Groups to Stormshield Groups

Configure in FreeRADIUS `/etc/freeradius/users`:

```conf
# VPN Admins - Full access
DEFAULT Ldap-Group == "VPN-Admins", Auth-Type := Accept
    Service-Type = Framed-User,
    Framed-Protocol = PPP,
    Framed-IP-Address = 10.70.0.0/24,
    Class = "admin-vpn",
    Stormshield-User-Group = "vpn-admin"

# Standard VPN Users
DEFAULT Ldap-Group == "VPN-Users", Auth-Type := Accept
    Service-Type = Framed-User,
    Framed-Protocol = PPP,
    Framed-IP-Address = 10.70.0.0/24,
    Class = "user-vpn",
    Stormshield-User-Group = "vpn-user"
```

### Stormshield Group Configuration

1. Navigate to **Configuration > Users > Groups**
2. Create groups matching RADIUS Class attribute:
   - `vpn-admin` - Administrator access
   - `vpn-user` - Standard user access

---

## Verification

### Test RADIUS Authentication

From Stormshield CLI:

```bash
# Test RADIUS authentication
TEST RADIUS SERVER="RoXX-RADIUS" USER="testuser" PASSWORD="testpass"
```

Expected output:
```
RADIUS authentication successful
User: testuser
Groups: vpn-user
```

### Debug RADIUS

```bash
# Enable RADIUS debug
CONFIG LOG SETPARAM LEVEL=DEBUG FILTER=RADIUS

# Monitor logs
MONITOR LOG FOLLOW filter=RADIUS
```

### View Active VPN Sessions

```bash
# IPsec sessions
SHOW IPSEC SA

# SSL-VPN sessions
SHOW VPN SSL SESSIONS

# All VPN users
SHOW VPN USERS
```

### Check RoXX Logs

Navigate to:
- `/config/radius-backends/logs` - Real-time authentication logs
- Filter by backend type, username, or success status

---

## Troubleshooting

### Issue: "RADIUS server unreachable"

**Solutions:**
1. Verify firewall rules allow UDP 1812/1813
2. Check network route from Stormshield to RoXX
3. Verify RADIUS server IP is correct

```bash
# Test connectivity
PING HOST="192.168.1.100" COUNT=4

# Check firewall rules
SHOW FILTER

# Test RADIUS port
TEST TCP HOST="192.168.1.100" PORT=1812
```

### Issue: "Authentication timeout"

**Debug Steps:**
1. Enable RADIUS debug: `CONFIG LOG SETPARAM LEVEL=DEBUG FILTER=RADIUS`
2. Check timeout value: `SHOW RADIUS`
3. Review RoXX logs for slow backend responses
4. Consider increasing cache TTL in RoXX

### Issue: "User authenticated but denied access"

**Solutions:**
1. Check firewall filter rules
2. Verify user group membership
3. Review authentication policy settings
4. Check IP pool availability

```bash
# View authentication policy
SHOW CONFIG POLICY AUTH NAME="VPN-RADIUS-Auth"

# Check IP pool usage
SHOW VPN IPPOOL
```

---

## RADIUS Attributes for Stormshield

### Standard Attributes

```conf
# User authentication
User-Name = "vpnuser"
User-Password = "password"

# Session parameters
Service-Type = Framed-User
Framed-Protocol = PPP
Framed-IP-Address = 10.70.0.50

# Session limits
Session-Timeout = 28800      # 8 hours
Idle-Timeout = 1800          # 30 minutes

# Group membership
Class = "vpn-user"
Filter-Id = "vpn-filter"
```

### Stormshield VSAs (Vendor-Specific)

```conf
# Stormshield-specific attributes
Stormshield-User-Group = "vpn-admin"
Stormshield-Firewall-Filter = "vpn-policy"
Stormshield-Bandwidth-Up = 10000      # KB/s
Stormshield-Bandwidth-Down = 10000    # KB/s
```

---

## High Availability Setup

### Primary + Secondary RADIUS

1. Navigate to **Configuration > Users > RADIUS servers**
2. Add secondary server:
   - **Name:** `RoXX-RADIUS-Backup`
   - **Server IP:** `192.168.1.101`
   - **Secret:** Same as primary
   - **Timeout:** `3` seconds

3. Update authentication policy to use both servers

### CLI Configuration

```bash
# Add backup RADIUS server
RADIUS SERVER ADD NAME="RoXX-RADIUS-Backup" \
  IPADDR="192.168.1.101" \
  SECRET="St0rmSh13ldR@dius!2024Secr3t" \
  AUTHPORT=1812 \
  TIMEOUT=3 \
  RETRY=2

# Update auth policy
CONFIG POLICY AUTH MODIFY NAME="VPN-RADIUS-Auth" \
  SERVER="RoXX-RADIUS" \
  BACKUPSERVER="RoXX-RADIUS-Backup"

CONFIG ACTIVATE
```

---

## Security Best Practices

1. **Strong Encryption:** Use AES-256-GCM for IPsec, TLS 1.2+ for SSL-VPN
2. **Certificate Validation:** Use valid SSL certificates, avoid self-signed in production
3. **MFA:** Integrate with MFA solution (TOTP/SMS)
4. **Logging:** Enable full logging for authentication and VPN events
5. **Session Limits:** Configure reasonable session and idle timeouts
6. **Access Control:** Implement least-privilege firewall rules
7. **Regular Updates:** Keep Stormshield firmware and RoXX updated

---

## Performance Optimization

### RoXX Cache Tuning

```python
# roxx/core/radius_backends/cache.py
AuthCache(
    ttl=600,        # 10 minutes cache
    max_size=500    # Support 500 concurrent users
)
```

### Stormshield Optimizations

```bash
# Reduce RADIUS timeout for faster failover
RADIUS SERVER MODIFY NAME="RoXX-RADIUS" TIMEOUT=3 RETRY=2

# Enable connection pooling
CONFIG VPN SETPARAM CONNPOOL=ENABLE MAXCONN=200
```

---

## Monitoring and Logs

### Stormshield Logs

```bash
# View authentication logs
MONITOR LOG FILTER=AUTH

# View VPN connections
MONITOR VPN CONNECTIONS

# View RADIUS communication
MONITOR LOG FILTER=RADIUS

# Export logs
LOG EXPORT TYPE=SYSLOG DEST="192.168.1.50:514"
```

### RoXX Dashboard

Real-time monitoring:
- **Auth Provider Logs:** `/config/auth-providers/logs`
- **RADIUS Backend Logs:** `/config/radius-backends/logs`
- **Statistics:** Success rate, cache hit rate, performance metrics

---

## Complete Working Example

### Scenario: 150 remote workers, LDAP backend

**Network Configuration:**
- Stormshield: `203.0.113.20`
- RoXX RADIUS: `10.0.0.100`
- VPN IP Pool: `10.70.0.10 - 10.70.0.200`
- Internal Network: `192.168.0.0/16`

**Stormshield Configuration:**

```bash
# RADIUS Server
RADIUS SERVER ADD NAME="RoXX-RADIUS" \
  IPADDR="10.0.0.100" \
  SECRET="xK9mP2nQ7wR5tY8uI3oP6aS4dF1" \
  AUTHPORT=1812 \
  TIMEOUT=5

# Authentication Policy
CONFIG POLICY AUTH ADD NAME="VPN-Auth" TYPE=RADIUS SERVER="RoXX-RADIUS"

# IPsec VPN
CONFIG VPN IPSEC MOBILE ADD NAME="Corp-VPN" \
  GATEWAY="vpn.company.com" \
  IKEVERSION=2 \
  IKEENCRYPTION=AES256 \
  IKEHASH=SHA256 \
  AUTHPOLICY="VPN-Auth" \
  IPPOOL="10.70.0.10-10.70.0.200" \
  DNS1="10.0.0.10"

# Firewall Rule
CONFIG FILTER ADDRULE NAME="VPN-Access" \
  SRC="10.70.0.0/24" \
  DST="192.168.0.0/16" \
  ACTION=PASS

CONFIG ACTIVATE
```

**RoXX Backend:**
- LDAP: `ldaps://dc.company.com:636`
- Bind DN: `uid={},ou=Users,dc=company,dc=com`
- Cache: 5min TTL, 200 entries

**Expected Performance:**
- Authentication: < 80ms (cached)
- Throughput: 150+ concurrent users
- Cache hit rate: 80-90%

---

## Client Configuration Examples

### Windows Client (IKEv2)

1. **Add VPN Connection**
   - Server: `vpn.company.com`
   - VPN Type: `IKEv2`
   - Authentication: `Username/Password`

2. **PowerShell Configuration:**
```powershell
Add-VpnConnection -Name "Corporate VPN" `
  -ServerAddress "vpn.company.com" `
  -TunnelType IKEv2 `
  -AuthenticationMethod EAP `
  -EncryptionLevel Required
```

### Linux Client (strongSwan)

```conf
# /etc/ipsec.conf
conn corporate-vpn
    keyexchange=ikev2
    left=%defaultroute
    leftauth=eap
    eap_identity=username@company.com
    right=vpn.company.com
    rightauth=pubkey
    rightid="vpn.company.com"
    auto=add
```

---

## Support

For issues or questions:
- Stormshield Documentation: https://documentation.stormshield.eu
- RoXX Debug Logs: `/config/radius-backends/logs`
- GitHub Issues: https://github.com/tsautier/RoXX/issues
