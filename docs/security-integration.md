# Rate Limiting and CSRF Integration Guide

## Current Status

✅ **Modules Created**:
- `roxx/core/security/rate_limit.py` - Rate limiting configuration
- `roxx/core/security/csrf.py` - CSRF token utilities
- `roxx/core/security/__init__.py` - Security module exports

✅ **App Integration**:
- Rate limiter middleware already integrated in `app.py` (lines 57-83)
- Custom rate limit exception handler with logging
- Audit logging for rate limit violations

---

## How to Apply Rate Limits to Routes

### 1. Import Required Decorators

```python
from roxx.core.security import limiter, get_rate_limit
```

### 2. Apply to Authentication Routes

**Login Route**:
```python
@app.post("/login")
@limiter.limit(get_rate_limit("login"))  # 5/minute
async def handle_login(request: Request, ...):
    # Login logic
    pass
```

**MFA Verification**:
```python
@app.post("/verify-totp")
@limiter.limit(get_rate_limit("totp_verify"))  # 10/minute
async def verify_totp(request: Request, ...):
    # TOTP verification logic
    pass
```

**WebAuthn**:
```python
@app.post("/webauthn/verify")
@limiter.limit(get_rate_limit("webauthn"))  # 10/minute
async def webauthn_verify(request: Request, ...):
    # WebAuthn logic
    pass
```

### 3. Apply to API Routes

**Write Operations**:
```python
@app.post("/api/admins")
@limiter.limit(get_rate_limit("api_write"))  # 30/minute
async def create_admin(request: Request, ...):
    pass

@app.delete("/api/admins/{username}")
@limiter.limit(get_rate_limit("api_write"))
async def delete_admin(request: Request, username: str):
    pass
```

**Read Operations**:
```python
@app.get("/api/admins")
@limiter.limit(get_rate_limit("api_read"))  # 60/minute
async def list_admins(request: Request):
    pass
```

### 4. Apply to SAML/Auth Provider Routes

```python
@app.post("/auth/saml/acs/{provider_id}")
@limiter.limit(get_rate_limit("saml_acs"))  # 20/minute  
async def saml_acs(request: Request, provider_id: int):
    pass

@app.post("/api/auth-providers")
@limiter.limit(get_rate_limit("auth_provider"))  # 30/minute
async def create_auth_provider(request: Request, ...):
    pass
```

---

## CSRF Protection Integration

### 1. Generate CSRF Token for Forms

In your route handlers that render forms:

```python
from roxx.core.security import generate_csrf_token

@app.get("/admins", response_class=HTMLResponse)
async def admins_page(request: Request, current_user: str = Depends(get_current_username)):
    csrf_token = generate_csrf_token()
    return templates.TemplateResponse("admins.html", {
        "request": request,
        "current_user": current_user,
        "csrf_token": csrf_token
    })
```

### 2. Add CSRF Token to HTML Forms

In your templates (e.g., `admins.html`):

```html
<form method="POST" action="/api/admins">
    <input type="hidden" name="_csrf_token" value="{{ csrf_token }}">
    <!-- Other form fields -->
    <button type="submit">Create Admin</button>
</form>
```

### 3. Validate CSRF Token in POST Routes

```python
from roxx.core.security import validate_csrf_token, get_csrf_token_from_request
from fastapi import HTTPException

@app.post("/api/admins")
async def create_admin(request: Request):
    # Extract and validate CSRF token
    csrf_token = get_csrf_token_from_request(request)
    if not validate_csrf_token(csrf_token):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")
    
    # Process form data
    form_data = await request.form()
    # ...
```

### 4. CSRF for AJAX Requests

For JavaScript/AJAX requests:

**Get token on page load**:
```javascript
// In your HTML template
<script>
    const csrfToken = "{{ csrf_token }}";
</script>
```

**Include in fetch requests**:
```javascript
fetch('/api/admins', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-CSRF-Token': csrfToken
    },
    body: JSON.stringify(data)
});
```

---

## Priority Routes to Protect

### High Priority (Implement First)
1. ✅ Login endpoint - **5/minute**
2. ✅ TOTP/WebAuthn verification - **10/minute**
3. ⚠️ Admin creation/deletion - **30/minute** + CSRF
4. ⚠️ MFA credential deletion - **30/minute** + CSRF
5. ⚠️ TOTP reset - **30/minute** + CSRF

### Medium Priority
6. SAML ACS endpoint - **20/minute**
7. Auth provider CRUD - **30/minute** + CSRF
8. Password changes - **10/minute** + CSRF
9. API token generation - **30/minute** + CSRF

### Low Priority
10. General API reads - **60/minute**
11. Static page views - **100/minute**

---

## Testing Rate Limits

### Manual Testing

```bash
# Test login rate limit (should block after 5 requests)
for i in {1..10}; do
  curl -X POST http://localhost:8000/login \
    -d "username=test&password=test" \
    -v | grep "429"
done
```

### Verify Headers

Rate limit responses include headers:
```
X-RateLimit-Limit: 5
X-RateLimit-Remaining: 4
X-RateLimit-Reset: 1642890123
```

---

## Configuration

### Adjust Rate Limits

Edit `roxx/core/security/rate_limit.py`:

```python
RATE_LIMITS = {
    "login": "5/minute",      # Decrease for tighter security
    "api_write": "30/minute", # Increase for higher traffic
    # ...
}
```

### Custom Limits for Specific Routes

```python
@app.post("/special-endpoint")
@limiter.limit("3/hour")  # Custom limit
async def special_endpoint():
    pass
```

---

## Monitoring

Rate limit violations are logged to:
1. **Application logs**: `logger.warning()`
2. **Audit logs**: Via `AuditManager.log()`

Query audit logs:
```sql
SELECT * FROM audit_logs 
WHERE action = 'RATE_LIMIT_EXCEEDED' 
ORDER BY timestamp DESC;
```

---

## Next Steps

1. Apply `@limiter.limit()` decorators to routes listed above
2. Add `csrf_token` to all form templates
3. Add CSRF validation to all POST/DELETE routes
4. Test rate limits with curl/Postman
5. Monitor audit logs for violations
6. Adjust limits based on real traffic patterns

---

## Security Benefits

✅ **Brute Force Protection**: Login limited to 5 attempts/minute  
✅ **MFA Bypass Prevention**: TOTP/WebAuthn limited to 10 attempts/minute  
✅ **API Abuse Prevention**: Write operations capped at 30/minute  
✅ **CSRF Attack Prevention**: Tokens required for state-changing operations  
✅ **Audit Trail**: All violations logged for security review

---

**Status**: Modules ready, integration guide complete  
**Estimated Integration Time**: 30-45 minutes  
**Recommended**: Apply in order of priority above
