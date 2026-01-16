# FreeRADIUS Installation Guide for Windows

This guide explains how to install and configure FreeRADIUS on Windows to work with RoXX.

---

## 🪟 Windows Challenge

**Important**: FreeRADIUS 3.x does not have an official Windows build. The recommended approach is to use **WSL2 (Windows Subsystem for Linux)**.

---

## ✅ Recommended Solution: WSL2 + Ubuntu

### Step 1: Install WSL2

```powershell
# Open PowerShell as Administrator

# Install WSL2
wsl --install

# Reboot your computer
```

After reboot, Ubuntu will be installed automatically.

### Step 2: Install FreeRADIUS in WSL

```bash
# Open Ubuntu (WSL)
# Update package list
sudo apt-get update

# Install FreeRADIUS
sudo apt-get install -y freeradius

# Verify installation
freeradius -v
# Should show: FreeRADIUS Version 3.0.x
```

### Step 3: Install Python in WSL

```bash
# Install Python 3.9+
sudo apt-get install -y python3 python3-pip

# Install RoXX dependencies
pip3 install rich questionary httpx cryptography msal loguru
```

### Step 4: Configure FreeRADIUS

```bash
# Stop FreeRADIUS
sudo systemctl stop freeradius

# Edit clients configuration
sudo nano /etc/freeradius/3.0/clients.conf

# Add test client:
# client localhost {
#     ipaddr = 127.0.0.1
#     secret = testing123
# }

# Configure exec module for RoXX
sudo nano /etc/freeradius/3.0/mods-enabled/exec
```

Add RoXX modules:
```
exec roxx_inwebo {
    wait = yes
    program = "python3 -m roxx.core.auth.inwebo"
    input_pairs = request
    output_pairs = reply
}

exec roxx_totp {
    wait = yes
    program = "python3 -m roxx.core.auth.totp"
    input_pairs = request
    output_pairs = reply
}
```

### Step 5: Copy RoXX to WSL

```powershell
# From Windows PowerShell
# Copy RoXX directory to WSL
wsl cp -r C:\RoXX /home/yourusername/roxx
```

Or from WSL:
```bash
# Access Windows files from WSL
cd /mnt/c/RoXX
```

### Step 6: Test FreeRADIUS

```bash
# Start FreeRADIUS in debug mode
sudo freeradius -X

# In another terminal, test authentication
echo "User-Name = testuser, User-Password = testpass" | \
  radclient -x localhost:1812 auth testing123
```

---

## 🐳 Alternative: Docker

### Install Docker Desktop

1. Download Docker Desktop for Windows
2. Enable WSL2 backend
3. Run FreeRADIUS container

```powershell
# Run FreeRADIUS in Docker
docker run -d --name freeradius \
  -p 1812:1812/udp \
  -p 1813:1813/udp \
  -v C:\RoXX\config:/etc/freeradius/3.0/mods-config \
  freeradius/freeradius-server:latest
```

### Configure Docker Container

```powershell
# Access container shell
docker exec -it freeradius bash

# Install Python
apt-get update && apt-get install -y python3 python3-pip

# Install RoXX dependencies
pip3 install rich httpx cryptography msal
```

---

## 🖥️ Alternative: Native Windows (Legacy)

### FreeRADIUS 2.x for Windows

**⚠️ Warning**: FreeRADIUS 2.x is outdated (2012) and not recommended.

1. Download from: http://freeradius.org/releases/
2. Install FreeRADIUS 2.2.x for Windows
3. Configure manually

**Limitations**:
- Old version (security risks)
- Limited features
- Poor Python integration
- Not actively maintained

---

## 🔧 RoXX Configuration for WSL

### Access WSL from Windows

RoXX Python modules can run on Windows and call FreeRADIUS in WSL:

```python
# roxx/utils/system.py - Add WSL detection
def is_wsl():
    """Check if running in WSL"""
    return 'microsoft' in platform.uname().release.lower()
```

### Network Configuration

WSL2 uses a virtual network. To access FreeRADIUS from Windows:

```bash
# Get WSL IP address
ip addr show eth0 | grep inet

# Configure Windows firewall to allow RADIUS
# Use WSL IP: 172.x.x.x
```

---

## 🧪 Testing Setup

### Test 1: FreeRADIUS Running

```bash
# In WSL
sudo systemctl status freeradius
# Should show: active (running)
```

### Test 2: RADIUS Authentication

```bash
# Test with radtest
radtest testuser testpass localhost 0 testing123
# Should show: Access-Accept or Access-Reject
```

### Test 3: RoXX Module

```bash
# Test TOTP module
export USER_NAME="testuser"
export USER_PASSWORD="123456"
python3 -m roxx.core.auth.totp
# Should return exit code 0 or 1
```

---

## 📊 Architecture Overview

```
┌─────────────────────────────────────────┐
│           Windows Host                   │
│                                          │
│  ┌────────────────────────────────────┐ │
│  │         WSL2 (Ubuntu)              │ │
│  │                                    │ │
│  │  ┌──────────────┐  ┌────────────┐ │ │
│  │  │ FreeRADIUS   │  │   RoXX     │ │ │
│  │  │   Server     │→ │  Python    │ │ │
│  │  │  (Port 1812) │  │  Modules   │ │ │
│  │  └──────────────┘  └────────────┘ │ │
│  │         ↓                ↓         │ │
│  │    [RADIUS]        [Auth APIs]    │ │
│  └────────────────────────────────────┘ │
│                                          │
│  Network Clients → WSL IP:1812          │
└─────────────────────────────────────────┘
```

---

## 🚀 Production Deployment

For production, we recommend:

1. **Linux Server**: Ubuntu 22.04 LTS or Debian 11
2. **Native FreeRADIUS**: Version 3.0.x
3. **RoXX**: Installed system-wide
4. **Systemd**: Service management

Windows with WSL2 is suitable for:
- ✅ Development
- ✅ Testing
- ✅ Small deployments
- ❌ Large-scale production (use Linux)

---

## 🆘 Troubleshooting

### Issue: WSL not starting

```powershell
# Enable WSL feature
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart

# Enable Virtual Machine Platform
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart

# Reboot
```

### Issue: FreeRADIUS won't start

```bash
# Check logs
sudo journalctl -u freeradius -n 50

# Test configuration
sudo freeradius -C

# Debug mode
sudo freeradius -X
```

### Issue: Python modules not found

```bash
# Install in WSL Python
pip3 install --user rich httpx cryptography

# Or use virtual environment
python3 -m venv /home/user/roxx-env
source /home/user/roxx-env/bin/activate
pip install -r requirements.txt
```

### Issue: Can't access from Windows

```bash
# In WSL, get IP
hostname -I

# In Windows, test connectivity
ping <WSL_IP>

# Configure Windows Firewall
# Allow UDP 1812, 1813
```

---

## 📚 Additional Resources

- [WSL2 Documentation](https://docs.microsoft.com/en-us/windows/wsl/)
- [FreeRADIUS Wiki](https://wiki.freeradius.org/)
- [Docker Desktop](https://www.docker.com/products/docker-desktop)
- [RoXX FreeRADIUS Integration](FREERADIUS_INTEGRATION.md)

---

**Recommendation**: Use WSL2 for Windows development, Linux server for production.
