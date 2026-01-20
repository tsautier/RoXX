# RoXX Deployment Guide

## Overview

This guide covers production deployment of RoXX RADIUS Authentication Proxy for enterprise VPN environments.

---

## Architecture Overview

```
┌─────────────────────────┐
│   VPN Clients (IKEv2)   │
└───────────┬─────────────┘
            │
┌───────────▼─────────────┐
│  Firewall (FortiGate/   │
│   Palo Alto/Stormshield)│
└───────────┬─────────────┘
            │ RADIUS (UDP 1812/1813)
┌───────────▼─────────────┐
│   FreeRADIUS Server     │
│   + RoXX Integration    │
└───────────┬─────────────┘
            │
┌───────────▼─────────────┐
│   Backend Databases     │
│  (LDAP/SQL/File)        │
└─────────────────────────┘
```

---

## System Requirements

### Minimum Requirements
- **OS:** Linux (Ubuntu 20.04+, Debian 11+, RHEL 8+)
- **CPU:** 2 cores
- **RAM:** 2 GB
- **Disk:** 10 GB
- **Network:** 1 Gbps NIC
- **Python:** 3.8+

### Recommended (Production)
- **OS:** Ubuntu 22.04 LTS or RHEL 9
- **CPU:** 4+ cores
- **RAM:** 8 GB
- **Disk:** 50 GB SSD
- **Network:** 10 Gbps NIC (redundant)
- **Python:** 3.10+

### For High Availability
- **Servers:** 2+ (active/standby or load balanced)
- **Load Balancer:** Optional (for >500 users)
- **Database:** PostgreSQL/MySQL for shared state
- **Monitoring:** Prometheus + Grafana

---

## Installation Methods

### Method 1: Standard Installation (Recommended)

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3 python3-pip python3-venv git freeradius

# Create application user
sudo useradd -r -s /bin/bash -d /opt/roxx roxx

# Clone repository
sudo -u roxx git clone https://github.com/tsautier/RoXX.git /opt/roxx/app
cd /opt/roxx/app

# Create virtual environment
sudo -u roxx python3 -m venv venv
sudo -u roxx venv/bin/pip install -r requirements.txt

# Create configuration directory
sudo mkdir -p /etc/roxx
sudo chown roxx:roxx /etc/roxx
```

### Method 2: Docker Deployment

```bash
# Clone repository
git clone https://github.com/tsautier/RoXX.git
cd RoXX

# Build Docker image
docker build -t roxx:v1.0.0-beta4 .

# Run container
docker run -d \
  --name roxx \
  -p 8000:8000 \
  -v /etc/roxx:/etc/roxx \
  -v /var/lib/roxx:/var/lib/roxx \
  roxx:v1.0.0-beta4
```

**Dockerfile:**
```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install dependencies
RUN apt-get update && \
    apt-get install -y gcc libldap2-dev libsasl2-dev && \
    rm -rf /var/lib/apt/lists/*

# Copy application
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY roxx/ ./roxx/
COPY docs/ ./docs/

# Create directories
RUN mkdir -p /etc/roxx /var/lib/roxx

# Expose ports
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s \
  CMD python -c "import requests; requests.get('http://localhost:8000/api/system/info')"

# Run application
CMD ["python", "-m", "roxx.web.app"]
```

### Method 3: System Service

Create `/etc/systemd/system/roxx.service`:

```ini
[Unit]
Description=RoXX RADIUS Authentication Proxy
After=network.target freeradius.service
Wants=freeradius.service

[Service]
Type=simple
User=roxx
Group=roxx
WorkingDirectory=/opt/roxx/app
Environment="PATH=/opt/roxx/app/venv/bin"
ExecStart=/opt/roxx/app/venv/bin/python -m roxx.web.app
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/roxx /etc/roxx

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable roxx
sudo systemctl start roxx
sudo systemctl status roxx
```

---

## FreeRADIUS Integration

### Install FreeRADIUS

```bash
# Ubuntu/Debian
sudo apt install -y freeradius freeradius-ldap freeradius-mysql freeradius-postgresql

# RHEL/CentOS
sudo dnf install -y freeradius freeradius-ldap freeradius-mysql freeradius-postgresql
```

### Configure RoXX Module

**Copy Python module:**
```bash
sudo cp /opt/roxx/app/roxx/integrations/freeradius_module.py \
  /etc/freeradius/3.0/mods-config/python/roxx_module.py

sudo chown freerad:freerad /etc/freeradius/3.0/mods-config/python/roxx_module.py
```

**Enable Python module:**

Edit `/etc/freeradius/3.0/mods-available/python`:
```python
python {
    module = roxx_module
    python_path = "/opt/roxx/app/venv/lib/python3.10/site-packages:/etc/freeradius/3.0/mods-config/python"
}
```

Enable module:
```bash
sudo ln -s /etc/freeradius/3.0/mods-available/python \
  /etc/freeradius/3.0/mods-enabled/python
```

**Configure authorize:**

Edit `/etc/freeradius/3.0/sites-available/default`:
```conf
authorize {
    preprocess
    python  # Add RoXX module
    # ... rest of config
}

authenticate {
    python  # Add RoXX module
    # ... rest of config
}
```

### Configure RADIUS Clients

Edit `/etc/roxx/radius_clients.conf`:
```conf
# FortiGate Firewall
client fortigate-fw {
    ipaddr = 192.168.1.10
    secret = YourStrongRadiusSecret123!
    shortname = fortigate
    nas_type = other
}

# Palo Alto Firewall
client paloalto-fw {
    ipaddr = 192.168.1.20
    secret = AnotherStrongSecret456!
    shortname = paloalto
    nas_type = other
}

# Stormshield Firewall
client stormshield-fw {
    ipaddr = 192.168.1.30
    secret = StormShieldSecret789!
    shortname = stormshield
    nas_type = other
}
```

Copy to FreeRADIUS:
```bash
sudo cp /etc/roxx/radius_clients.conf /etc/freeradius/3.0/clients.conf
sudo chown freerad:freerad /etc/freeradius/3.0/clients.conf
```

### Restart Services

```bash
# Test FreeRADIUS config
sudo freeradius -X

# If OK (Ctrl+C to stop), restart normally
sudo systemctl restart freeradius
sudo systemctl restart roxx
```

---

## Backend Configuration

### LDAP Backend (Active Directory)

**Web UI Configuration:**
1. Navigate to `/config/radius-backends`
2. Click **"+ Add Backend"**
3. Select **LDAP**
4. Configure:
   - **Name:** Corporate AD
   - **Server:** `ldaps://dc.company.com:636`
   - **Bind DN:** `cn={},ou=VPN Users,dc=company,dc=com`
   - **Use TLS:** ✓
   - **Priority:** 10

**Test Connection:**
- **Username:** `test.user`
- **Password:** `TestPassword123`
- Click **"Test Connection"**

### SQL Backend (PostgreSQL)

**Create Database:**
```sql
CREATE DATABASE radius;
CREATE USER radius_user WITH PASSWORD 'SecurePassword123';
GRANT ALL PRIVILEGES ON DATABASE radius TO radius_user;

\c radius

CREATE TABLE users (
    username VARCHAR(64) PRIMARY KEY,
    password VARCHAR(255) NOT NULL,  -- BCrypt hash
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert test user (password: 'test123')
INSERT INTO users (username, password) VALUES 
('vpnuser1', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5jtJ3sdCyZSpy');
```

**RoXX Configuration:**
- **Backend Type:** SQL
- **DB Type:** PostgreSQL
- **Host:** `localhost`
- **Port:** `5432`
- **Database:** `radius`
- **Username:** `radius_user`
- **Password:** `SecurePassword123`
- **Password Type:** BCrypt

### File Backend

**Create users file:**
```bash
sudo nano /etc/roxx/users.conf
```

```conf
# Format: username:password_hash:enabled
# BCrypt hash for 'test123'
vpnuser1:$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5jtJ3sdCyZSpy:1
vpnuser2:$2b$12$K9pP.gN8Q1nM2Lxm3OeP4u5RrEwW6Yxy7ZtAaBbCcDdEeFfGgHhIi:1
```

**RoXX Configuration:**
- **Backend Type:** File
- **File Path:** `/etc/roxx/users.conf`
- **Password Type:** BCrypt

---

## Security Hardening

### Firewall Configuration

```bash
# Allow only necessary ports
sudo ufw allow 22/tcp     # SSH
sudo ufw allow 8000/tcp   # RoXX Web UI (restrict to admin network)
sudo ufw allow 1812/udp   # RADIUS Auth
sudo ufw allow 1813/udp   # RADIUS Accounting
sudo ufw enable
```

### SSL/TLS Certificates

**For Production Web UI:**

```bash
# Install certbot
sudo apt install -y certbot

# Get Let's Encrypt certificate
sudo certbot certonly --standalone -d roxx.company.com

# Configure RoXX to use SSL
# Edit roxx/web/app.py to add SSL context
```

**For LDAPS:**

```bash
# Ensure LDAP server has valid certificate
# Test connection:
openssl s_client -connect dc.company.com:636 -showcerts
```

### API Token Security

1. **Generate Tokens via UI:** `/config/api-tokens`
2. **Use Strong Names:** "Production-Server-1", "Monitoring-System"
3. **Rotate Regularly:** Every 90 days
4. **Revoke Unused:** Monitor `last_used` field
5. **Secure Storage:** Use secrets management (Vault, AWS Secrets Manager)

### Database Encryption

```bash
# Encrypt SQLite databases
sudo apt install -y sqlcipher

# Use encrypted database for tokens
# Place in /var/lib/roxx/ with restricted permissions
sudo chown roxx:roxx /var/lib/roxx/*.db
sudo chmod 600 /var/lib/roxx/*.db
```

---

## Monitoring & Logging

### Application Logs

**View Live Logs:**
```bash
# Systemd journal
sudo journalctl -u roxx -f

# Application logs
sudo tail -f /var/log/roxx/app.log
```

**Log Rotation:**

Create `/etc/logrotate.d/roxx`:
```conf
/var/log/roxx/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 roxx roxx
    sharedscripts
    postrotate
        systemctl reload roxx
    endscript
}
```

### FreeRADIUS Logs

```bash
# Enable detailed logging
sudo nano /etc/freeradius/3.0/radiusd.conf
```

```conf
log {
    destination = files
    file = /var/log/freeradius/radius.log
    auth = yes
    auth_badpass = yes
    auth_goodpass = yes
}
```

### Prometheus Metrics

**Add metrics endpoint** (future enhancement):
```python
# roxx/web/app.py
from prometheus_client import Counter, Histogram, make_asgi_app

auth_requests = Counter('roxx_auth_requests_total', 'Total auth requests')
auth_duration = Histogram('roxx_auth_duration_seconds', 'Auth duration')

# Mount metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)
```

---

## High Availability Setup

### Active-Passive Configuration

**Primary Server:**
```bash
# Configure as normal
# IP: 192.168.1.100
```

**Secondary Server:**
```bash
# Install RoXX identically
# IP: 192.168.1.101
# Use same configuration files
# Sync databases (rsync or PostgreSQL replication)
```

**Firewall Configuration:**
```bash
# Configure both servers in RADIUS client config
# Primary: 192.168.1.100
# Secondary: 192.168.1.101 (as backup)
```

### Active-Active with Load Balancer

**HAProxy Configuration:**

```conf
frontend radius_in
    bind *:1812
    mode tcp
    default_backend radius_servers

backend radius_servers
    mode tcp
    balance leastconn
    server radius1 192.168.1.100:1812 check inter 2000
    server radius2 192.168.1.101:1812 check inter 2000
    server radius3 192.168.1.102:1812 check inter 2000
```

### Database Replication

**PostgreSQL Streaming Replication:**

**Primary server:**
```sql
-- Create replication user
CREATE ROLE replicator WITH REPLICATION LOGIN PASSWORD 'ReplPassword';
```

Edit `postgresql.conf`:
```conf
wal_level = replica
max_wal_senders = 3
wal_keep_size = 64
```

**Standby server:**
```bash
# Stop PostgreSQL
sudo systemctl stop postgresql

# Clone from primary
pg_basebackup -h 192.168.1.100 -D /var/lib/postgresql/14/main \
  -U replicator -P --wal-method=stream

# Start standby
sudo systemctl start postgresql
```

---

## Performance Tuning

### Application Tuning

**Cache Settings:**
```python
# roxx/core/radius_backends/cache.py
AuthCache(
    ttl=600,        # 10 minutes
    max_size=1000   # Support 1000 concurrent users
)
```

**Uvicorn Workers:**
```bash
# For high traffic
uvicorn roxx.web.app:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker
```

### FreeRADIUS Tuning

Edit `/etc/freeradius/3.0/radiusd.conf`:
```conf
thread pool {
    start_servers = 32
    max_servers = 256
    min_spare_servers = 8
    max_spare_servers = 64
}
```

### System Limits

Edit `/etc/security/limits.conf`:
```conf
roxx soft nofile 65536
roxx hard nofile 65536
freerad soft nofile 65536
freerad hard nofile 65536
```

Edit `/etc/sysctl.conf`:
```conf
# Network tuning
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.ipv4.tcp_rmem = 4096 87380 16777216
net.ipv4.tcp_wmem = 4096 65536 16777216

# Connection tracking
net.netfilter.nf_conntrack_max = 262144
```

Apply:
```bash
sudo sysctl -p
```

---

## Backup & Recovery

### Backup Script

```bash
#!/bin/bash
# /opt/roxx/backup.sh

BACKUP_DIR="/var/backups/roxx"
DATE=$(date +%Y%m%d-%H%M%S)

mkdir -p $BACKUP_DIR

# Backup databases
cp ~/.roxx/*.db $BACKUP_DIR/db-$DATE/

# Backup configuration
tar -czf $BACKUP_DIR/config-$DATE.tar.gz /etc/roxx/

# Backup FreeRADIUS config
tar -czf $BACKUP_DIR/freeradius-$DATE.tar.gz /etc/freeradius/

# Remove old backups (>30 days)
find $BACKUP_DIR -type f -mtime +30 -delete

echo "Backup completed: $DATE"
```

**Cron Job:**
```bash
# Daily backup at 2 AM
0 2 * * * /opt/roxx/backup.sh >> /var/log/roxx/backup.log 2>&1
```

### Recovery

```bash
# Restore databases
cp /var/backups/roxx/db-20260119-020000/*.db ~/.roxx/

# Restore configuration
tar -xzf /var/backups/roxx/config-20260119-020000.tar.gz -C /

# Restart services
sudo systemctl restart roxx freeradius
```

---

## Troubleshooting

### Common Issues

#### Issue: "RADIUS server not responding"

**Debug:**
```bash
# Test FreeRADIUS
sudo freeradius -X

# Check port
sudo netstat -ulnp | grep 1812

# Test locally
echo "User-Name=test,User-Password=test" | \
  radclient -x localhost auth testing123
```

#### Issue: "Authentication failed"

**Check:**
1. RoXX logs: `/config/radius-backends/logs`
2. FreeRADIUS logs: `/var/log/freeradius/radius.log`
3. Backend connectivity
4. Credentials

**Debug:**
```bash
# Test backend directly
python3 -c "
from roxx.core.radius_backends.ldap_backend import LDAPBackend
backend = LDAPBackend('ldaps://dc.company.com:636', ...)
result = backend.authenticate('testuser', 'testpass')
print(result)
"
```

#### Issue: "High latency"

**Solutions:**
1. Enable caching (check cache hit rate in logs)
2. Add more FreeRADIUS workers
3. Optimize LDAP queries
4. Add database indexes
5. Consider load balancing

---

## Production Checklist

### Pre-Deployment

- [ ] System requirements met
- [ ] All dependencies installed
- [ ] FreeRADIUS configured and tested
- [ ] Backends configured and tested
- [ ] RADIUS clients configured
- [ ] Firewall rules applied
- [ ] SSL certificates installed
- [ ] Monitoring configured
- [ ] Backup system in place
- [ ] Documentation reviewed

### Security Checklist

- [ ] Strong RADIUS shared secrets (20+ chars)
- [ ] API tokens generated and secured
- [ ] Database encryption enabled
- [ ] File permissions locked down (`600` for sensitive files)
- [ ] Firewall rules restricting access
- [ ] LDAPS (not LDAP) for backend connections
- [ ] Regular security updates enabled
- [ ] Log retention policy defined
- [ ] Incident response plan documented

###Post-Deployment

- [ ] Authentication tested from all firewalls
- [ ] VPN connection successful
- [ ] Logs monitoring confirmed
- [ ] Performance metrics within acceptable range
- [ ] Backup tested and verified
- [ ] Documentation updated
- [ ] Team trained on operations
- [ ] Runbook created for common tasks

---

## Support & Resources

- **GitHub:** https://github.com/tsautier/RoXX
- **Documentation:** `/docs` folder
- **Issues:** https://github.com/tsautier/RoXX/issues
- **VPN Guides:** See `docs/VPN_INTEGRATION_*.md`

---

**RoXX is ready for production!** 🚀
