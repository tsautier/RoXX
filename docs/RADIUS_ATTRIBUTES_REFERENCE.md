# RADIUS Attributes Reference for VPN Integration

## Overview

This document provides a comprehensive reference of RADIUS attributes commonly used in VPN integrations with Fortigate, Palo Alto, and Stormshield firewalls.

---

## Standard RADIUS Attributes (RFC 2865)

### User Authentication

| Attribute ID | Attribute Name | Type | Description | Example |
|--------------|----------------|------|-------------|---------|
| 1 | User-Name | string | Username for authentication | `john.doe` |
| 2 | User-Password | string | User password (encrypted) | `(encrypted)` |
| 4 | NAS-IP-Address | ipaddr | IP of NAS (VPN gateway) | `192.168.1.10` |
| 5 | NAS-Port | integer | Physical port number | `0` |
| 31 | Calling-Station-Id | string | Client MAC/IP address | `00:11:22:33:44:55` |
| 32 | NAS-Identifier | string | VPN gateway hostname | `vpn-gateway-1` |

### Session Parameters

| Attribute ID | Attribute Name | Type | Description | Example |
|--------------|----------------|------|-------------|---------|
| 6 | Service-Type | integer | Type of service | `2` (Framed) |
| 7 | Framed-Protocol | integer | Protocol to use | `1` (PPP) |
| 8 | Framed-IP-Address | ipaddr | Assign static IP | `10.10.10.50` |
| 9 | Framed-IP-Netmask | ipaddr | Network mask | `255.255.255.0` |
| 10 | Framed-Routing | integer | Routing method | `0` (None) |
| 13 | Framed-Compression | integer | Compression type | `1` (Van Jacobsen) |
| 22 | Framed-Route | string | Static route | `192.168.10.0/24` |

### Session Control

| Attribute ID | Attribute Name | Type | Description | Example |
|--------------|----------------|------|-------------|---------|
| 27 | Session-Timeout | integer | Max session duration (sec) | `28800` (8 hours) |
| 28 | Idle-Timeout | integer | Max idle time (sec) | `1800` (30 min) |
| 25 | Class | string | User class/group | `vpn-users` |
| 11 | Filter-Id | string | Filter/ACL name | `vpn-filter` |

### Accounting

| Attribute ID | Attribute Name | Type | Description | Example |
|--------------|----------------|------|-------------|---------|
| 40 | Acct-Status-Type | integer | Accounting event type | `1` (Start) |
| 41 | Acct-Delay-Time | integer | Delay in seconds | `0` |
| 42 | Acct-Input-Octets | integer | Bytes received | `1048576` |
| 43 | Acct-Output-Octets | integer | Bytes sent | `2097152` |
| 44 | Acct-Session-Id | string | Unique session ID | `session-12345` |
| 45 | Acct-Authentic | integer | Auth method used | `1` (RADIUS) |
| 46 | Acct-Session-Time | integer | Session duration (sec) | `3600` |

---

## Vendor-Specific Attributes (VSAs)

### Fortinet FortiGate (Vendor ID: 12356)

| Attribute | Type | Description | Example |
|-----------|------|-------------|---------|
| Fortinet-Group-Name | string | User group name | `VPN-Users` |
| Fortinet-Vdom-Name | string | Virtual domain | `root` |
| Fortinet-Client-IP-Address | ipaddr | Assigned VPN IP | `10.10.10.50` |
| Fortinet-Access-Profile | string | Access permission profile | `full-access` |
| Fortinet-Webfilter-Profile | string | Web filtering profile | `default-webfilter` |
| Fortinet-AV-Profile | string | Antivirus profile | `default-av` |
| Fortinet-IPS-Profile | string | IPS profile | `default-ips` |

**FreeRADIUS Configuration:**
```conf
DEFAULT Ldap-Group == "VPN-Admins"
    Fortinet-Group-Name = "admin",
    Fortinet-Vdom-Name = "root",
    Fortinet-Access-Profile = "super-admin"
```

### Palo Alto Networks (Vendor ID: 25461)

| Attribute | Type | Description | Example |
|-----------|------|-------------|---------|
| PAN-User-Group | string | User group | `GlobalProtect-Users` |
| PAN-Admin-Role | string | Admin role | `superuser` |
| PAN-Panorama-Admin-Role | string | Panorama role | `device-admin` |
| PAN-User-Privilege-Level | string | Privilege level | `normal` / `admin` |
| PAN-Portal | string | GlobalProtect portal | `GP-Portal` |
| PAN-Gateway | string | GlobalProtect gateway | `GP-Gateway` |
| PAN-Domain | string | Virtual system | `vsys1` |

**FreeRADIUS Configuration:**
```conf
DEFAULT Ldap-Group == "VPN-Users"
    PAN-User-Group = "GlobalProtect-Users",
    PAN-User-Privilege-Level = "normal",
    PAN-Portal = "GP-Portal",
    PAN-Gateway = "GP-Gateway"
```

### Stormshield (Vendor ID: 11256)

| Attribute | Type | Description | Example |
|-----------|------|-------------|---------|
| Stormshield-User-Group | string | User group | `vpn-users` |
| Stormshield-Firewall-Filter | string | Firewall policy | `vpn-policy` |
| Stormshield-Bandwidth-Up | integer | Upload bandwidth (KB/s) | `10000` |
| Stormshield-Bandwidth-Down | integer | Download bandwidth (KB/s) | `10000` |
| Stormshield-Session-Timeout | integer | Max session time (sec) | `28800` |
| Stormshield-Idle-Timeout | integer | Max idle time (sec) | `1800` |

**FreeRADIUS Configuration:**
```conf
DEFAULT Ldap-Group == "VPN-Admins"
    Stormshield-User-Group = "vpn-admin",
    Stormshield-Firewall-Filter = "admin-policy",
    Stormshield-Bandwidth-Up = 100000,
    Stormshield-Bandwidth-Down = 100000
```

---

## Common Use Cases

### 1. Assign Static IP to Specific User

**FreeRADIUS `/etc/freeradius/users`:**
```conf
john.doe    Cleartext-Password := "password"
    Service-Type = Framed-User,
    Framed-Protocol = PPP,
    Framed-IP-Address = 10.10.10.100,
    Framed-IP-Netmask = 255.255.255.0
```

### 2. Group-Based Access Control

**LDAP + FreeRADIUS:**
```conf
# Admin users - Full access
DEFAULT Ldap-Group == "Domain Admins", Auth-Type := Accept
    Service-Type = Framed-User,
    Class = "admin",
    Session-Timeout = 86400,
    Fortinet-Group-Name = "admin",
    PAN-User-Group = "GlobalProtect-Admins",
    Stormshield-User-Group = "vpn-admin"

# Standard users - Limited access
DEFAULT Ldap-Group == "VPN-Users", Auth-Type := Accept
    Service-Type = Framed-User,
    Class = "user",
    Session-Timeout = 28800,
    Idle-Timeout = 1800,
    Fortinet-Group-Name = "user",
    PAN-User-Group = "GlobalProtect-Users",
    Stormshield-User-Group = "vpn-user"

# Contractors - Restricted
DEFAULT Ldap-Group == "Contractors", Auth-Type := Accept
    Service-Type = Framed-User,
    Class = "contractor",
    Session-Timeout = 14400,
    Idle-Timeout = 900,
    Filter-Id = "contractor-acl",
    Fortinet-Group-Name = "contractor",
    Stormshield-Bandwidth-Up = 1000,
    Stormshield-Bandwidth-Down = 1000
```

### 3. Dynamic VLAN Assignment

```conf
# Sales team - Sales VLAN
DEFAULT Ldap-Group == "Sales", Auth-Type := Accept
    Tunnel-Type = VLAN,
    Tunnel-Medium-Type = IEEE-802,
    Tunnel-Private-Group-Id = "100"  # VLAN 100

# Engineering - Engineering VLAN
DEFAULT Ldap-Group == "Engineering", Auth-Type := Accept
    Tunnel-Type = VLAN,
    Tunnel-Medium-Type = IEEE-802,
    Tunnel-Private-Group-Id = "200"  # VLAN 200
```

### 4. Bandwidth Limiting

```conf
# Free tier - Limited bandwidth
DEFAULT Ldap-Group == "Free-Users", Auth-Type := Accept
    Stormshield-Bandwidth-Up = 1000,      # 1 MB/s
    Stormshield-Bandwidth-Down = 2000,    # 2 MB/s
    Session-Timeout = 3600                 # 1 hour max

# Premium tier - High bandwidth
DEFAULT Ldap-Group == "Premium-Users", Auth-Type := Accept
    Stormshield-Bandwidth-Up = 100000,    # 100 MB/s
    Stormshield-Bandwidth-Down = 100000,
    Session-Timeout = 86400                # 24 hours max
```

### 5. Split Tunneling Routes

```conf
# Push specific routes for split tunneling
DEFAULT Auth-Type := Accept
    Framed-Route = "192.168.0.0/16 10.10.10.1 1",
    Framed-Route += "10.0.0.0/8 10.10.10.1 1",
    Framed-Route += "172.16.0.0/12 10.10.10.1 1"
```

---

## RoXX RADIUS Attribute Configuration

### LDAP Backend with Attributes

In RoXX, configure your LDAP backend to map LDAP groups to RADIUS attributes:

**FreeRADIUS `/etc/freeradius/mods-available/ldap`:**
```conf
ldap {
    server = 'ldaps://dc.company.com'
    identity = 'cn=radius,ou=Service Accounts,dc=company,dc=com'
    password = 'RadiusServicePassword'
    base_dn = 'dc=company,dc=com'
    
    user {
        base_dn = "ou=VPN Users,${..base_dn}"
        filter = "(uid=%{%{Stripped-User-Name}:-%{User-Name}})"
    }
    
    group {
        base_dn = "ou=Groups,${..base_dn}"
        filter = '(objectClass=groupOfNames)'
        membership_attribute = 'member'
    }
}
```

### SQL Backend with Attributes

**Database Schema:**
```sql
CREATE TABLE radcheck (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(64) NOT NULL,
    attribute VARCHAR(64) NOT NULL,
    op VARCHAR(2) NOT NULL,
    value VARCHAR(253) NOT NULL
);

CREATE TABLE radreply (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(64) NOT NULL,
    attribute VARCHAR(64) NOT NULL,
    op VARCHAR(2) NOT NULL,
    value VARCHAR(253) NOT NULL
);

CREATE TABLE radgroupcheck (
    id INT PRIMARY KEY AUTO_INCREMENT,
    groupname VARCHAR(64) NOT NULL,
    attribute VARCHAR(64) NOT NULL,
    op VARCHAR(2) NOT NULL,
    value VARCHAR(253) NOT NULL
);

CREATE TABLE radgroupreply (
    id INT PRIMARY KEY AUTO_INCREMENT,
    groupname VARCHAR(64) NOT NULL,
    attribute VARCHAR(64) NOT NULL,
    op VARCHAR(2) NOT NULL,
    value VARCHAR(253) NOT NULL
);
```

**Example Data:**
```sql
-- User authentication
INSERT INTO radcheck (username, attribute, op, value) 
VALUES ('john.doe', 'Cleartext-Password', ':=', 'password123');

-- User-specific attributes
INSERT INTO radreply (username, attribute, op, value) VALUES
('john.doe', 'Framed-IP-Address', '=', '10.10.10.100'),
('john.doe', 'Session-Timeout', '=', '28800'),
('john.doe', 'Class', '=', 'admin');

-- Group-based attributes
INSERT INTO radgroupreply (groupname, attribute, op, value) VALUES
('VPN-Admins', 'Fortinet-Group-Name', '=', 'admin'),
('VPN-Admins', 'PAN-User-Group', '=', 'GlobalProtect-Admins'),
('VPN-Admins', 'Session-Timeout', '=', '86400');

INSERT INTO radgroupreply (groupname, attribute, op, value) VALUES
('VPN-Users', 'Fortinet-Group-Name', '=', 'user'),
('VPN-Users', 'PAN-User-Group', '=', 'GlobalProtect-Users'),
('VPN-Users', 'Session-Timeout', '=', '28800'),
('VPN-Users', 'Idle-Timeout', '=', '1800');
```

---

## Debugging RADIUS Attributes

### Test Authentication with radtest

```bash
# Basic test
radtest john.doe password123 localhost 0 testing123

# Test with specific NAS
radtest john.doe password123 192.168.1.100 0 testing123 \
    NAS-IP-Address=192.168.1.10

# With multiple attributes
echo "User-Name = john.doe, User-Password = password123, NAS-IP-Address = 192.168.1.10" | \
radclient -x localhost auth testing123
```

### FreeRADIUS Debug Mode

```bash
# Stop FreeRADIUS
systemctl stop freeradius

# Run in debug mode
freeradius -X

# In another terminal, test
radtest john.doe password123 localhost 0 testing123
```

**Look for in debug output:**
```
(0) Received Access-Request Id 123 from 127.0.0.1:45678 to 0.0.0.0:1812 length 74
(0)   User-Name = "john.doe"
(0)   User-Password = "password123"
...
(0) Sent Access-Accept Id 123 from 0.0.0.0:1812 to 127.0.0.1:45678 length 0
(0)   Framed-IP-Address = 10.10.10.100
(0)   Session-Timeout = 28800
(0)   Class = "admin"
```

### Packet Capture

```bash
# Capture RADIUS traffic
tcpdump -i any -n port 1812 -w radius.pcap

# View with Wireshark
wireshark radius.pcap
```

---

## Best Practices

1. **Secure Secrets:** Use strong, unique RADIUS shared secrets (20+ characters)
2. **Minimal Attributes:** Only send necessary attributes to reduce packet size
3. **Group-Based:** Use LDAP groups for attribute assignment instead of per-user config
4. **Test Thoroughly:** Verify all attributes with different firewalls
5. **Monitor Logs:** Regularly review RoXX logs at `/config/radius-backends/logs`
6. **Cache Wisely:** Enable caching in RoXX for frequently accessed attributes
7. **Document:** Maintain documentation of custom attribute mappings

---

## Reference Links

- **RFC 2865:** RADIUS Protocol
- **RFC 2866:** RADIUS Accounting
- **RFC 2867:** RADIUS Tunnel Authentication
- **RFC 3162:** RADIUS and IPv6
- **Fortinet RADIUS VSAs:** FortiOS Documentation
- **Palo Alto RADIUS:** PAN-OS Admin Guide
- **Stormshield RADIUS:** SNS Administration Guide
- **FreeRADIUS Dictionary:** `/usr/share/freeradius/dictionary.*`

---

## Support

For attribute-related issues:
- Check RoXX logs: `/config/radius-backends/logs`
- Enable FreeRADIUS debug: `freeradius -X`
- GitHub Issues: https://github.com/tsautier/RoXX/issues
