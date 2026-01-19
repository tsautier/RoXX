# FreeRADIUS Integration Guide

## Overview
RoXX provides **dual integration** with FreeRADIUS:
1. **rlm_python** (recommended) - Direct Python module for low latency
2. **REST API** - HTTP endpoint for flexibility

## Method 1: rlm_python (Recommended)

### Installation

1. **Install FreeRADIUS Python Module**
   ```bash
   # Ubuntu/Debian
   apt-get install freeradius-python3
   
   # RHEL/CentOS
   yum install freeradius-python3
   ```

2. **Copy RoXX Module Configuration**
   ```bash
   cp /path/to/roxx/freeradius/roxx-module.conf /etc/freeradius/3.0/mods-available/roxx
   ln -s ../mods-available/roxx /etc/freeradius/3.0/mods-enabled/roxx
   ```

3. **Edit Module Configuration**
   ```bash
   nano /etc/freeradius/3.0/mods-enabled/roxx
   ```
   
   Update `mod_path` to point to your RoXX installation:
   ```
   python roxx {
       mod_path = "/opt/roxx"  # or wherever RoXX is installed
       module = "roxx.integrations.freeradius_module"
       func_authorize = authorize
       func_authenticate = authenticate
       func_post_auth = post_auth
   }
   ```

4. **Enable RoXX in Site Configuration**
   ```bash
   nano /etc/freeradius/3.0/sites-enabled/default
   ```
   
   Add `roxx` to authorize and authenticate sections:
   ```
   authorize {
       preprocess
       chap
       mschap
       roxx  # Add here
       ...
   }
   
   authenticate {
       Auth-Type PAP {
           roxx  # Add here
       }
       Auth-Type CHAP {
           roxx  # Add here
       }
       Auth-Type MS-CHAP {
           mschap
       }
   }
   ```

5. **Restart FreeRadIUS**
   ```bash
   systemctl restart freeradius
   systemctl status freeradius
   ```

### Testing

```bash
# Test authentication
radtest testuser testpass localhost 0 testing123

# Check logs
tail -f /var/log/freeradius/radius.log
```

## Method 2: REST API

### Configuration

1. **Configure rlm_rest Module**
   ```bash
   nano /etc/freeradius/3.0/mods-enabled/rest
   ```
   
   Add RoXX REST configuration:
   ```
   rest roxx_rest {
       uri = "http://localhost:8000/api/radius-auth"
       method = 'post'
       body = 'json'
       
       authorize {
           uri = "${...uri}"
           method = 'post'
           body = 'json'
       }
       
       authenticate {
           uri = "${...uri}"
           method = 'post'
           body = 'json'
           
           # Map RADIUS attributes to JSON
           data = "{
               \"username\": \"%{User-Name}\",
               \"password\": \"%{User-Password}\"
           }"
       }
   }
   ```

2. **Enable in Site Configuration**
   ```
   authenticate {
       roxx_rest
   }
   ```

## Performance Comparison

| Method | Latency | Complexity | Recommended For |
|--------|---------|------------|-----------------|
| rlm_python | ~1-2ms | Low | Production |
| REST API | ~5-10ms | Very Low | Testing, External Systems |

## Troubleshooting

### rlm_python Issues

**Module not loading:**
```bash
# Check Python path
python3 -c "from roxx.integrations.freeradius_module import *; print('OK')"

# Check FreeRADIUS debug
freeradius -X
```

**Import errors:**
```bash
# Set ROXX_PATH environment variable
export ROXX_PATH=/opt/roxx
systemctl restart freeradius
```

### REST API Issues

**Connection refused:**
- Ensure RoXX web app is running: `python -m roxx.web.app`
- Check firewall rules

**Authentication fails:**
- Check RoXX logs: `tail -f ~/.roxx/logs/roxx.log`
- Verify backend configuration in web UI

## Security Notes

- **rlm_python** runs in FreeRADIUS process - very secure
- **REST API** requires authentication - ensure firewall rules
- Both methods use the same backend manager
- Backends are tried in priority order
- Successful authentications are cached (5 min TTL)

## Next Steps

1. Configure RADIUS backends in web UI: http://localhost:8000/config/radius-backends
2. Test with `radtest`
3. Monitor authentication logs
4. Adjust backend priorities as needed
