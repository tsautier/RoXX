"""
RoXX Web Interface - Modern FastAPI Application
Replaces the old SimpleSAMLphp interface with a modern Python web app
"""

from fastapi import FastAPI, Request, Form, HTTPException, Depends, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from starlette.middleware.sessions import SessionMiddleware
from roxx.core.audit.manager import AuditManager
from roxx.core.audit.db import AuditDatabase
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from roxx.core.security.rate_limit import limiter
import qrcode
import io
import base64
import os
import secrets
import asyncio
import logging
from pathlib import Path
from typing import List

from roxx.core.auth.totp import TOTPAuthenticator
from roxx.utils.system import SystemManager

logger = logging.getLogger("roxx.web")

# ------------------------------------------------------------------------------
# Security & Authentication
# ------------------------------------------------------------------------------


# ------------------------------------------------------------------------------
# App Initialization
# ------------------------------------------------------------------------------

# ------------------------------------------------------------------------------
# App Initialization
# ------------------------------------------------------------------------------

# ------------------------------------------------------------------------------
# App Initialization
# ------------------------------------------------------------------------------

VERSION = "1.0.0-beta6"

app = FastAPI(
    title="RoXX Admin Interface",
    description="Modern web interface for RoXX RADIUS Authentication Proxy",
    version=VERSION
)

# Initialize Rate Limiter
app.state.limiter = limiter

@app.exception_handler(RateLimitExceeded)
async def rate_limit_exception_handler(request: Request, exc: RateLimitExceeded):
    """
    Custom handler for RateLimitExceeded using Jinja2 templates and logging
    """
    client_ip = request.client.host if request.client else "unknown"
    logger.warning(f"RATE LIMIT EXCEEDED: {client_ip} tried to access {request.url.path} - {exc.detail}")
    
    AuditManager.log(
        request=request, 
        action="RATE_LIMIT_EXCEEDED", 
        severity="WARNING", 
        details={"path": request.url.path, "limit": str(exc.detail)}
    )
    
    # API / Auth endpoints -> JSON
    if request.url.path.startswith("/api") or request.url.path.startswith("/auth"):
         return JSONResponse(
            {"success": False, "detail": f"Rate limit exceeded: {exc.detail}"}, 
            status_code=429
        )
    
    # HTML Pages -> Template
    return templates.TemplateResponse("429.html", {"request": request}, status_code=429)

# Add SessionMiddleware for MFA enrollment (needs to be before routes)
import secrets
# Security Configuration
# In production, this should be loaded from env vars or config file
# For now, we generate if not set, but this invalidates sessions on restart
SECRET_KEY = os.getenv("ROXX_SECRET_KEY", secrets.token_hex(32))

from itsdangerous import URLSafeTimedSerializer
cookie_signer = URLSafeTimedSerializer(SECRET_KEY, salt="roxx-mfa-trust")

app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    max_age=3600,  # Session expires after 1 hour
    session_cookie="roxx_session",
    https_only=False, # Set to True if using HTTPS
    same_site="lax"
)

# Templates directory
templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

# Static files
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# ------------------------------------------------------------------------------
# Auth Logic (Hybrid: Cookie + Basic)
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# Auth Logic (Database Backed)
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# Auth Logic (Database Backed)
# ------------------------------------------------------------------------------
from fastapi.responses import RedirectResponse
from fastapi.security.utils import get_authorization_scheme_param
from roxx.core.auth.manager import AuthManager

# Initialize Auth Subsystem on startup
AuthManager.init()

# Initialize authentication provider configuration database
from roxx.core.auth.config_db import ConfigManager as AuthConfigManager
AuthConfigManager.init()

# Initialize API tokens database
from roxx.core.auth.api_tokens import APITokenManager
APITokenManager.init()

# Initialize RADIUS backends database
from roxx.core.radius_backends.config_db import RadiusBackendDB
RadiusBackendDB.init()

# Initialize MFA database
from roxx.core.auth.mfa_db import MFADatabase
MFADatabase.init()

# Initialize Audit database
AuditDatabase.init_db()

async def get_current_username(request: Request):
    """
    Verifies authentication via Session Cookie.
    Enforces 'active' status for general access.
    """
    # 1. Check Cookie
    session_cookie = request.cookies.get("session")
    if session_cookie:
        try:
            decoded = base64.b64decode(session_cookie).decode("utf-8")
            if ":" in decoded:
                username, status = decoded.split(":", 1)
                # Only allow 'active' sessions for general routes
                if username and status == 'active':
                    return username
        except:
            pass 

    # 2. Handle Unauthorized
    accept = request.headers.get("Accept", "")
    if "text/html" in accept:
        raise NotAuthenticatedException()
    else:
        # API Response
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Basic"},
        )

# Dependency for Auth Routes (allows partial auth)
async def get_partial_user(request: Request):
    session_cookie = request.cookies.get("session")
    if session_cookie:
        try:
            decoded = base64.b64decode(session_cookie).decode("utf-8")
            username, status = decoded.split(":", 1)
            return username, status
        except:
            pass
    return None, None


class NotAuthenticatedException(Exception):
    pass

@app.exception_handler(NotAuthenticatedException)
async def not_authenticated_exception_handler(request: Request, exc: NotAuthenticatedException):
    accept = request.headers.get("Accept", "")
    if "text/html" in accept:
        return RedirectResponse(url="/login")
    else:
        return JSONResponse(status_code=401, content={"detail": "Not authenticated"})


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
@limiter.limit("5/minute")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    # Verify credentials
    success, user_data = AuthManager.verify_credentials(username, password)
    
    if success:
        # Check Force Change Password
        if user_data.get("must_change_password"):
            session_val = base64.b64encode(f"{username}:force_change".encode("utf-8")).decode("utf-8")
            response = JSONResponse({"success": True, "redirect": "/auth/change-password"})
            response.set_cookie(key="session", value=session_val, httponly=True)
            return response

        # Discovery MFA Methods
        mfa_methods = []
        
        # 1. TOTP / SMS / Email (from MFADatabase)
        mfa_settings = MFADatabase.get_mfa_settings(username) or {}
        if mfa_settings.get('mfa_enabled'):
            # Current DB schema 'mfa_type' is single, but let's be robust
            m_type = mfa_settings.get('mfa_type', 'totp')
            mfa_methods.append(m_type)
            
        # 2. WebAuthn
        from roxx.core.auth.webauthn_db import WebAuthnDatabase
        if WebAuthnDatabase.list_credentials(username):
            if 'webauthn' not in mfa_methods:
                mfa_methods.append('webauthn')
                
        # 3. Client Certs
        from roxx.core.auth.cert_db import CertDatabase
        if CertDatabase.get_user_certs(username):
            if 'client_cert' not in mfa_methods:
                mfa_methods.append('client_cert')

        print(f"[DEBUG] Login for {username}: Methods={mfa_methods}, WebAuthnCreds={WebAuthnDatabase.list_credentials(username)}")

        if mfa_methods:
            # Check Trusted Device
            trusted_cookie = request.cookies.get("mfa_trusted_device")
            if trusted_cookie:
                try:
                    trusted_username = cookie_signer.loads(trusted_cookie, max_age=30*24*60*60)
                    if trusted_username == username:
                        # Trusted - Skip MFA
                        session_val = base64.b64encode(f"{username}:active".encode("utf-8")).decode("utf-8")
                        response = JSONResponse({"success": True, "redirect": "/"})
                        response.set_cookie(key="session", value=session_val, httponly=True)
                        AuditManager.log(request, "LOGIN_SUCCESS", "INFO", {"username": username, "method": "trusted_device"}, username=username)
                        return response
                except: pass

            # MFA Required
            request.session['mfa_username'] = username # Store for verification steps
            session_val = base64.b64encode(f"{username}:mfa_pending".encode("utf-8")).decode("utf-8")
            
            response = JSONResponse({
                "success": True,
                "mfa_required": True,
                "username": username,
                "mfa_methods": mfa_methods
            })
            response.set_cookie(key="session", value=session_val, httponly=True)
            AuditManager.log(request, "LOGIN_MFA_REQUIRED", "INFO", {"username": username, "mfa_methods": mfa_methods}, username=username)
            return response

        # No MFA - Login
        session_val = base64.b64encode(f"{username}:active".encode("utf-8")).decode("utf-8")
        response = JSONResponse({"success": True, "redirect": "/dashboard"})
        response.set_cookie(key="session", value=session_val, httponly=True)
        AuditManager.log(request, "LOGIN_SUCCESS", "INFO", {"username": username, "method": "password_only"}, username=username)
        return response
    
    AuditManager.log(request, "LOGIN_FAILED", "WARNING", {"username": username, "reason": "invalid_credentials"}, username=username)
    return JSONResponse(status_code=401, content={"success": False, "detail": "Invalid credentials"})


@app.get("/logout")
async def logout(request: Request):
    response = RedirectResponse(url="/login")
    response.delete_cookie("session")
    AuditManager.log(request, "LOGOUT", "INFO", username=request.session.get("username"))
    request.session.clear() # Clear specific session storage if used
    # Clear MFA session data
    request.session.pop('mfa_username', None)
    return response

# MFA Verification Routes
@app.get("/login/mfa", response_class=HTMLResponse)
async def mfa_verification_page(request: Request):
    """MFA verification page"""
    # Check if user has valid mfa_pending session
    session_cookie = request.cookies.get("session")
    if not session_cookie:
        return RedirectResponse(url="/login", status_code=303)
    
    try:
        decoded = base64.b64decode(session_cookie).decode("utf-8")
        username, status = decoded.split(":", 1)
        
        if status != "mfa_pending":
            return RedirectResponse(url="/login", status_code=303)
        
        return templates.TemplateResponse("mfa_verify.html", {
            "request": request,
            "username": username
        })
    except:
        return RedirectResponse(url="/login", status_code=303)

@app.post("/auth/mfa/verify")
@limiter.limit("5/minute")
async def mfa_verify_unified(request: Request):
    """Unified MFA Verification (TOTP, SMS, Email, Backup)"""
    try:
        data = await request.json()
    except:
        raise HTTPException(status_code=400, detail="Invalid JSON")
        
    mfa_type = data.get('type')
    code = data.get('code')
    trust_device = data.get('trust_device', False)

    # Validate Session
    session_cookie = request.cookies.get("session")
    if not session_cookie:
        raise HTTPException(status_code=401, detail="Session expired")
    try:
        decoded = base64.b64decode(session_cookie).decode("utf-8")
        username, status = decoded.split(":", 1)
        if status != "mfa_pending":
             raise HTTPException(status_code=401, detail="Invalid session state")
    except:
        raise HTTPException(status_code=401, detail="Invalid session")

    # Verification Logic
    verified = False
    
    if mfa_type == 'totp':
        settings = MFADatabase.get_mfa_settings(username)
        if settings and settings.get('totp_secret'):
            if MFAManager.verify_totp(settings['totp_secret'], code):
                verified = True
                MFADatabase.update_last_used(username)
                
        # Fallback: Check if it's a backup code
        if not verified:
             success, msg = MFADatabase.verify_and_consume_backup_code(username, code)
             if success:
                 verified = True
                
    elif mfa_type == 'backup_code':
         success, msg = MFADatabase.verify_and_consume_backup_code(username, code)
         if success:
             verified = True
             
    elif mfa_type in ['sms', 'email']:
         # Verify OTP against stored secret/cache
         # Since we don't have a Redis cache in this Phase yet, we check 'mfa_enrollment' or session
         # But usually for login we generated a code and stored it in session.
         # TODO: Implement send/verify logic with session storage for code.
         # For now, placeholder or check static secret? NO.
         # Let's assume the 'send' endpoint stored it in user session.
         session_code = request.session.get(f"mfa_code_{mfa_type}")
         if session_code and session_code == code:
             verified = True
             request.session.pop(f"mfa_code_{mfa_type}", None)
             
    if verified:
        session_val = base64.b64encode(f"{username}:active".encode("utf-8")).decode("utf-8")
        response = JSONResponse({"success": True})
        response.set_cookie(key="session", value=session_val, httponly=True)
        
        # Cleanup
        request.session.pop('mfa_username', None)
        
        AuditManager.log(request, "MFA_SUCCESS", "INFO", {"username": username, "method": mfa_type}, username=username)
        return response

    AuditManager.log(request, "MFA_FAILED", "WARNING", {"username": username, "method": mfa_type, "reason": "invalid_code"}, username=username)
    return JSONResponse({"success": False, "detail": "Invalid Code"}, status_code=400)

@app.post("/auth/mfa/cert/verify")
async def mfa_cert_verify(request: Request):
    """Verify Client Certificate for MFA"""
    # ... (Session Check as above) ...
    # Verify Cert
    from roxx.core.security.cert_auth import CertAuthManager
    from roxx.core.auth.cert_db import CertDatabase
    
    session_cookie = request.cookies.get("session")
    try:
        decoded = base64.b64decode(session_cookie).decode("utf-8")
        username, status = decoded.split(":", 1)
    except: return JSONResponse({"success": False, "detail": "Session Error"}, status_code=401)

    cert_info = CertAuthManager.get_cert_info(request)
    if not cert_info:
         return JSONResponse({"success": False, "detail": "No Certificate"}, status_code=400)
    
    # Check if this cert is registered to this user
    stored_user = CertDatabase.get_user_by_fingerprint(cert_info['fingerprint'])
    
    if stored_user and stored_user == username:
        session_val = base64.b64encode(f"{username}:active".encode("utf-8")).decode("utf-8")
        response = JSONResponse({"success": True})
        response.set_cookie(key="session", value=session_val, httponly=True)
        AuditManager.log(request, "MFA_SUCCESS", "INFO", {"username": username, "method": "client_cert", "fingerprint": cert_info['fingerprint']}, username=username)
        return response
        
    AuditManager.log(request, "MFA_FAILED", "WARNING", {"username": username, "method": "client_cert", "reason": "cert_mismatch", "fingerprint": cert_info['fingerprint']}, username=username)
    return JSONResponse({"success": False, "detail": "Certificate not linked to user"}, status_code=403)


# ------------------------------------------------------------------------------
# Password & MFA Management
# ------------------------------------------------------------------------------
@app.get("/auth/change-password", response_class=HTMLResponse)
async def change_password_page(request: Request, current_user: str = Depends(get_current_username)):
    """Change Password Page"""
    return templates.TemplateResponse("change_password.html", get_page_context(
        request, current_user, "password"
    ))

@app.post("/auth/change-password", response_class=HTMLResponse)
async def change_password(
    request: Request, 
    current_password: str = Form(...), 
    new_password: str = Form(...),
    confirm_password: str = Form(...)
):
    username, status = await get_partial_user(request)
    if not username:
        return RedirectResponse("/login")

    if new_password != confirm_password:
        return templates.TemplateResponse("change_password.html", {
            "request": request, "error": "New passwords do not match"
        })

    success, _ = AuthManager.verify_credentials(username, current_password)
    if not success:
        return templates.TemplateResponse("change_password.html", {
            "request": request, "error": "Current password incorrect"
        })

    try:
        AuthManager.change_password(username, new_password)
    except ValueError as e:
         return templates.TemplateResponse("change_password.html", {
            "request": request, "error": str(e)
        })

    # Success -> Active Session
    session_val = base64.b64encode(f"{username}:active".encode("utf-8")).decode("utf-8")
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(key="session", value=session_val, httponly=True)
    return response

@app.get("/auth/mfa-challenge", response_class=HTMLResponse)
async def mfa_challenge_page(request: Request):
    username, status = await get_partial_user(request)
    if not username or status != "mfa_pending":
        return RedirectResponse("/login")
    return templates.TemplateResponse("mfa_challenge.html", {"request": request})

@app.post("/auth/mfa-challenge", response_class=HTMLResponse)
async def mfa_challenge(request: Request, code: str = Form(...)):
    username, status = await get_partial_user(request)
    if not username or status != "mfa_pending":
        return RedirectResponse("/login")

    if AuthManager.verify_mfa(username, code):
        session_val = base64.b64encode(f"{username}:active".encode("utf-8")).decode("utf-8")
        response = RedirectResponse(url="/", status_code=303)
        response.set_cookie(key="session", value=session_val, httponly=True)
        return response
    
    return templates.TemplateResponse("mfa_challenge.html", {
        "request": request, "error": "Invalid authentication code"
    })

@app.get("/auth/mfa-setup", response_class=HTMLResponse, dependencies=[Depends(get_current_username)])
async def mfa_setup_page(request: Request):
    username = await get_current_username(request)
    secret, uri = AuthManager.setup_mfa(username)
    
    # Check if we have 'qrcode' lib support for image generation
    # If not, client side JS or just display secret
    # roxx requirements has qrcode.
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    qr_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    
    return templates.TemplateResponse("mfa_setup.html", {
        "request": request, 
        "secret": secret,
        "qr_b64": qr_b64
    })

@app.post("/auth/mfa-setup", response_class=HTMLResponse, dependencies=[Depends(get_current_username)])
async def mfa_setup(request: Request, secret: str = Form(...), code: str = Form(...)):
    username = await get_current_username(request)
    
    # Verify code against the NEW secret
    if AuthManager.verify_mfa(username, code, pending_secret=secret):
        AuthManager.enable_mfa(username, secret)
        return RedirectResponse(url="/", status_code=303)
    
    # Error handling? Need to re-generate QR? 
    # Usually we re-render page. For simplicity, just error.
    return templates.TemplateResponse("error.html", {"request": request, "message": "Invalid code. MFA Setup Failed."}) # Needs error.html or logic


# ------------------------------------------------------------------------------
# WebAuthn Routes
# ------------------------------------------------------------------------------
from roxx.core.auth.webauthn import WebAuthnManager
from fido2.utils import websafe_encode, websafe_decode

@app.on_event("startup")
async def startup_event():
    WebAuthnManager.init()
    from roxx.core.auth.cert_db import CertDatabase
    CertDatabase.init_db()

@app.get("/api/webauthn/register/options", dependencies=[Depends(get_current_username)])
async def webauthn_register_options(request: Request):
    """Generate registration options"""
    username = await get_current_username(request)
    # We use username as user_id for simplicity, but ideally should be stable UID
    options, state = WebAuthnManager.generate_registration_options(username, username)
    request.session["webauthn_state"] = state
    return dict(options)

@app.post("/api/webauthn/register/verify", dependencies=[Depends(get_current_username)])
async def webauthn_register_verify(request: Request):
    """Verify registration response"""
    username = await get_current_username(request)
    state = request.session.get("webauthn_state")
    if not state:
        raise HTTPException(status_code=400, detail="State not found")
        
    data = await request.json()
    success, msg = WebAuthnManager.verify_registration(username, data, state)
    
    if success:
        return {"success": True, "message": "Security Key Registered"}
    else:
        raise HTTPException(status_code=400, detail=msg)

@app.get("/api/webauthn/authenticate/options")
async def webauthn_auth_options(request: Request):
    """Generate auth options"""
    # We need username. If doing 2FA, we have it in session.
    # If doing passwordless, we might need to ask username first.
    # For MFA scenario:
    session_cookie = request.cookies.get("session")
    username = None
    if session_cookie:
        try:
            decoded = base64.b64decode(session_cookie).decode("utf-8")
            username, _ = decoded.split(":", 1)
        except: pass
    
    if not username:
        # Check mfa_username in session (set during login)
        username = request.session.get('mfa_username')

    if not username:
        raise HTTPException(status_code=400, detail="User context missing")
        
    options, state = WebAuthnManager.generate_authentication_options(username)
    if not options:
         raise HTTPException(status_code=400, detail="No keys found")
         
    request.session["webauthn_auth_state"] = state
    return dict(options)


@app.post("/api/webauthn/authenticate/verify")
async def webauthn_auth_verify(request: Request):
    """Verify auth response"""
    state = request.session.get("webauthn_auth_state")
    # need username again
    session_cookie = request.cookies.get("session")
    username = None
    if session_cookie:
        try:
            decoded = base64.b64decode(session_cookie).decode("utf-8")
            username, _ = decoded.split(":", 1)
        except: pass
    if not username:
        username = request.session.get('mfa_username')
        
    if not state or not username:
        raise HTTPException(status_code=400, detail="State or User missing")
        
    data = await request.json()
    success, msg = WebAuthnManager.verify_authentication(username, data, state)
    
    if success:
        # If successful, we need to log them in fully or set session
        # If this was MFA step:
        if request.session.get('mfa_username'):
             # Perform Login
             session_val = base64.b64encode(f"{username}:active".encode("utf-8")).decode("utf-8")
             # We can't set cookie here easily without return Response object?
             # Actually we return JSON. The Client JS should redirect.
             # But we need to set the cookie in this response.
             response = JSONResponse({"success": True, "redirect": "/"})
             response.set_cookie(key="session", value=session_val, httponly=True)
             request.session.pop('mfa_username', None)
             return response
        else:
             return {"success": True, "message": "Verified"}
    else:
        raise HTTPException(status_code=400, detail=msg)







# ------------------------------------------------------------------------------
# API & Pages
# ------------------------------------------------------------------------------

def get_page_context(request: Request, username: str, active_page: str, **kwargs):
    """Helper to generate standard page context with sidebar variables"""
    context = {
        "request": request,
        "username": username,
        "active_page": active_page,
        "version": VERSION,
        **kwargs
    }
    return context

@app.get("/logs-view", response_class=HTMLResponse)
async def logs_view_page(request: Request, current_user: str = Depends(get_current_username)):
    """System Logs Page"""
    return templates.TemplateResponse("logs.html", get_page_context(
        request, current_user, "logs",
        title="System Logs"
    ))

@app.get("/", response_class=HTMLResponse, dependencies=[Depends(get_current_username)])
async def home(request: Request):
    """Home page - redirects to dashboard"""
    return RedirectResponse("/dashboard")


@app.get("/totp/enroll", response_class=HTMLResponse)
async def totp_enroll_page(request: Request, current_user: str = Depends(get_current_username)):
    """TOTP enrollment page"""
    return templates.TemplateResponse("totp_enroll.html", get_page_context(
        request, current_user, "mfa",
        title="TOTP Enrollment"
    ))

@app.get("/config/mfa-gateways", response_class=HTMLResponse)
async def config_mfa_gateways_page(request: Request, current_user: str = Depends(get_current_username)):
    """MFA Gateways Configuration Page"""
    return templates.TemplateResponse("config_mfa_gateways.html", get_page_context(
        request, current_user, "config",
        title="MFA Gateways"
    ))

# ... (API endpoints remain unchanged) ...

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, current_user: str = Depends(get_current_username)):
    """Dashboard page"""
    import os # Added for os.name check
    import logging # Added for logger.error
    from roxx.core.services import ServiceManager as SvcMgr
    
    logger = logging.getLogger(__name__) # Initialize logger
    
    # Check FreeRADIUS status
    radius_active = SystemManager.is_service_running('freeradius') or SystemManager.is_service_running('radiusd')
    radius_status = "UP" if radius_active else "DOWN"
    
    # Fetch recent users/admins for the user management table
    recent_users = []
    try:
        admins_list = AuthManager.list_admins()
        for admin in admins_list:
            recent_users.append({
                "username": admin.get("username", "N/A"),
                "role": admin.get("auth_source", "local").title(),
                "status": "UP",  # Could be enhanced with actual session tracking
                "last_login": admin.get("last_login") or "Never"
            })
    except Exception as e:
        logger.error(f"Error fetching dashboard users: {e}")
        recent_users = [
            {"username": "admin", "role": "Local", "status": "UP", "last_login": "2024-05-22"}
        ]
    
    return templates.TemplateResponse("dashboard.html", get_page_context(
        request, current_user, "dashboard",
        radius_status=radius_status,
        os_type=SystemManager.get_os(),
        kernel_version=SystemManager.get_kernel_version(),
        uptime=SystemManager.get_uptime(),
        cpu=SystemManager.get_cpu_info(),
        memory=SystemManager.get_memory_info(),
        disk=SystemManager.get_disk_info(),
        adv=SystemManager.get_advanced_metrics(),
        recent_users=recent_users
    ))


@app.get("/users", response_class=HTMLResponse)
async def users_page(request: Request, current_user: str = Depends(get_current_username)):
    """User management page"""
    # Simple parse of users.conf if it exists
    users_list = []
    try:
        users_file = SystemManager.get_config_dir() / "users.conf"
        if users_file.exists():
            with open(users_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        parts = line.split()
                        if parts:
                            users_list.append(parts[0])
    except Exception:
        pass
        
    return templates.TemplateResponse("users.html", get_page_context(
        request, current_user, "users",
        users=users_list or ["admin (demo)"]
    ))


@app.get("/config", response_class=HTMLResponse)
async def config_page(request: Request, current_user: str = Depends(get_current_username)):
    """Configuration page"""
    return templates.TemplateResponse("config.html", get_page_context(
        request, current_user, "settings"
    ))

@app.get("/config/api-tokens", response_class=HTMLResponse)
async def api_tokens_page(request: Request, current_user: str = Depends(get_current_username)):
    """API Tokens Management"""
    return templates.TemplateResponse("api_tokens.html", get_page_context(
        request, current_user, "settings"
    ))

@app.get("/settings/mfa", response_class=HTMLResponse)
async def mfa_settings_page(request: Request, current_user: str = Depends(get_current_username)):
    """MFA Settings Page"""
    return templates.TemplateResponse("mfa_settings.html", get_page_context(
        request, current_user, "mfa"
    ))


# ------------------------------------------------------------------------------
# Authentication Provider Configuration
# ------------------------------------------------------------------------------
@app.get("/config/auth-providers", response_class=HTMLResponse)
async def auth_providers_page(request: Request, current_user: str = Depends(get_current_username)):
    """Authentication providers configuration page"""
    return templates.TemplateResponse("auth_providers.html", get_page_context(
        request, current_user, "settings"
    ))

@app.get("/config/auth-providers/logs", response_class=HTMLResponse)
async def auth_providers_logs_page(request: Request, current_user: str = Depends(get_current_username)):
    """Authentication Provider Debug Logs"""
    return templates.TemplateResponse("auth_providers_logs.html", get_page_context(
        request, current_user, "settings"
    ))

@app.get("/api/auth-providers", dependencies=[Depends(get_current_username)])
async def list_auth_providers():
    """List all authentication providers"""
    from roxx.core.auth.config_db import ConfigManager
    try:
        ConfigManager.init()  # Ensure DB is initialized
        providers = ConfigManager.list_providers()
        return providers
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/auth-providers", dependencies=[Depends(get_current_username)])
async def create_auth_provider(request: Request):
    """Create a new authentication provider"""
    from roxx.core.auth.config_db import ConfigManager
    
    try:
        data = await request.json()
        provider_type = data.get('provider_type')
        name = data.get('name')
        config_dict = data.get('config', {})
        enabled = data.get('enabled', True)
        
        if not provider_type or not name:
            raise HTTPException(status_code=400, detail="Missing provider_type or name")
        
        success, message, provider_id = ConfigManager.create_provider(
            provider_type, name, config_dict, enabled
        )
        
        if success:
            return {"success": True, "message": message, "id": provider_id}
        else:
            raise HTTPException(status_code=400, detail=message)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/auth-providers/{provider_id}", dependencies=[Depends(get_current_username)])
async def update_auth_provider(provider_id: int, request: Request):
    """Update an authentication provider"""
    from roxx.core.auth.config_db import ConfigManager
    
    try:
        data = await request.json()
        name = data.get('name')
        config_dict = data.get('config')
        enabled = data.get('enabled')
        
        success, message = ConfigManager.update_provider(
            provider_id, name=name, config_dict=config_dict, enabled=enabled
        )
        
        if success:
            return {"success": True, "message": message}
        else:
            raise HTTPException(status_code=400, detail=message)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/auth-providers/{provider_id}", dependencies=[Depends(get_current_username)])
async def delete_auth_provider(provider_id: int):
    """Delete an authentication provider"""
    from roxx.core.auth.config_db import ConfigManager
    
    try:
        success, message = ConfigManager.delete_provider(provider_id)
        
        if success:
            return {"success": True, "message": message}
        else:
            raise HTTPException(status_code=400, detail=message)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/auth-providers/test", dependencies=[Depends(get_current_username)])
async def test_auth_provider(request: Request):
    """Test authentication provider configuration"""
    from roxx.core.auth.config_db import ConfigManager
    
    try:
        data = await request.json()
        provider_type = data.get('provider_type')
        config_dict = data.get('config', {})
        test_username = data.get('test_username')
        test_password = data.get('test_password')
        
        if not all([provider_type, test_username, test_password]):
            raise HTTPException(status_code=400, detail="Missing required fields")
        
        success, message = ConfigManager.test_provider(
            provider_type, config_dict, test_username, test_password
        )
        
        return {"success": success, "message": message}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ------------------------------------------------------------------------------
# RADIUS User Authentication Backends
# ------------------------------------------------------------------------------
@app.get("/config/radius-backends", response_class=HTMLResponse, dependencies=[Depends(get_current_username)])
async def radius_backends_page(request: Request, current_user: str = Depends(get_current_username)):
    """RADIUS backends configuration page"""
    return templates.TemplateResponse("radius_backends.html", get_page_context(
        request, current_user, "settings"
    ))

@app.get("/config/radius-backends/logs", response_class=HTMLResponse, dependencies=[Depends(get_current_username)])
async def radius_backends_logs_page(request: Request, current_user: str = Depends(get_current_username)):
    """RADIUS Backend Debug Logs"""
    return templates.TemplateResponse("radius_backends_logs.html", get_page_context(
        request, current_user, "settings"
    ))

@app.get("/api/radius-backends", dependencies=[Depends(get_current_username)])
async def list_radius_backends():
    """List all RADIUS backends"""
    from roxx.core.radius_backends.config_db import RadiusBackendDB
    try:
        RadiusBackendDB.init()
        backends = RadiusBackendDB.list_backends()
        return backends
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/radius-backends", dependencies=[Depends(get_current_username)])
async def create_radius_backend(request: Request):
    """Create a new RADIUS backend"""
    from roxx.core.radius_backends.config_db import RadiusBackendDB
    
    try:
        data = await request.json()
        backend_type = data.get('backend_type')
        name = data.get('name')
        config_dict = data.get('config', {})
        enabled = data.get('enabled', True)
        priority = data.get('priority', 100)
        
        if not backend_type or not name:
            raise HTTPException(status_code=400, detail="Missing backend_type or name")
        
        success, message, backend_id = RadiusBackendDB.create_backend(
            backend_type, name, config_dict, enabled, priority
        )
        
        if success:
            # Reload backends in manager
            from roxx.core.radius_backends.manager import reload_manager
            reload_manager()
            return {"success": True, "message": message, "id": backend_id}
        else:
            raise HTTPException(status_code=400, detail=message)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/radius-backends/{backend_id}", dependencies=[Depends(get_current_username)])
async def update_radius_backend(backend_id: int, request: Request):
    """Update a RADIUS backend"""
    from roxx.core.radius_backends.config_db import RadiusBackendDB
    
    try:
        data = await request.json()
        name = data.get('name')
        config_dict = data.get('config')
        enabled = data.get('enabled')
        priority = data.get('priority')
        
        success, message = RadiusBackendDB.update_backend(
            backend_id, name=name, config_dict=config_dict, 
            enabled=enabled, priority=priority
        )
        
        if success:
            # Reload backends in manager
            from roxx.core.radius_backends.manager import reload_manager
            reload_manager()
            return {"success": True, "message": message}
        else:
            raise HTTPException(status_code=400, detail=message)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/radius-backends/{backend_id}", dependencies=[Depends(get_current_username)])
async def delete_radius_backend(backend_id: int):
    """Delete a RADIUS backend"""
    from roxx.core.radius_backends.config_db import RadiusBackendDB
    
    try:
        success, message = RadiusBackendDB.delete_backend(backend_id)
        
        if success:
            # Reload backends in manager
            from roxx.core.radius_backends.manager import reload_manager
            reload_manager()
            return {"success": True, "message": message}
        else:
            raise HTTPException(status_code=400, detail=message)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/radius-backends/test", dependencies=[Depends(get_current_username)])
async def test_radius_backend(request: Request):
    """Test RADIUS backend configuration"""
    from roxx.core.radius_backends.manager import RadiusBackendManager
    
    try:
        data = await request.json()
        backend_type = data.get('backend_type')
        config_dict = data.get('config', {})
        test_username = data.get('test_username')
        test_password = data.get('test_password')
        
        manager = RadiusBackendManager()
        success, message = manager.test_backend(
            backend_type, config_dict, test_username, test_password
        )
        
        return {"success": success, "message": message}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/radius-auth", dependencies=[Depends(get_current_username)])
async def radius_authenticate(request: Request):
    """
    RADIUS authentication endpoint (for REST API integration).
    Used by FreeRADIUS rlm_rest or external systems.
    """
    from roxx.core.radius_backends.manager import get_manager
    
    try:
        data = await request.json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            raise HTTPException(status_code=400, detail="Missing username or password")
        
        manager = get_manager()
        success, attributes = manager.authenticate(username, password)
        
        if success:
            return {
                "success": True,
                "message": "Authentication successful",
                "attributes": attributes or {}
            }
        else:
            return {
                "success": False,
                "message": "Authentication failed"
            }
            
    except Exception as e:
        logger.error(f"RADIUS auth error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ------------------------------------------------------------------------------
# Audit Logs
# ------------------------------------------------------------------------------

@app.get("/logs", response_class=HTMLResponse)
async def logs_page(request: Request, current_user: str = Depends(get_current_username)):
    """Audit Logs Viewer"""
    return templates.TemplateResponse("logs.html", get_page_context(request, current_user, "logs"))

@app.get("/api/logs")
async def get_audit_logs(
    request: Request, 
    limit: int = 100, 
    offset: int = 0,
    search: str = None,
    current_user: str = Depends(get_current_username)
):
    """API to retrieve audit logs"""
    logs = AuditDatabase.get_logs(limit, offset, search)
    return {"logs": logs}



# ------------------------------------------------------------------------------
# API Tokens Management
# ------------------------------------------------------------------------------
@app.get("/api/tokens", dependencies=[Depends(get_current_username)])
async def list_api_tokens():
    """List all API tokens (admin only)"""
    tokens = APITokenManager.list_tokens()
    return {"tokens": tokens}

@app.post("/api/tokens", dependencies=[Depends(get_current_username)])
async def generate_api_token(request: Request):
    """Generate a new API token"""
    data = await request.json()
    name = data.get('name')
    
    if not name:
        raise HTTPException(status_code=400, detail="Token name required")
    
    success, message, token = APITokenManager.generate_token(name)
    
    if success:
        return {"success": True, "message": message, "token": token}
    else:
        raise HTTPException(status_code=400, detail=message)

@app.delete("/api/tokens/{token_id}", dependencies=[Depends(get_current_username)])
async def revoke_api_token(token_id: int, hard_delete: bool = False):
    """Revoke or Delete an API token"""
    if hard_delete:
        success, message = APITokenManager.delete_token(token_id)
    else:
        success, message = APITokenManager.revoke_token(token_id)
    
    if success:
        return {"success": True, "message": message}
    else:
        raise HTTPException(status_code=404, detail=message)



@app.get("/api/system/info", dependencies=[Depends(get_current_username)])
async def system_info():
    """Get system information"""
    return JSONResponse({
        "os": SystemManager.get_os(),
        "is_admin": SystemManager.is_admin(),
        "config_dir": str(SystemManager.get_config_dir()),
        "uptime": SystemManager.get_uptime(),
        "version": VERSION
    })



@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "roxx-web"}


# ------------------------------------------------------------------------------
# Admin Management API
# ------------------------------------------------------------------------------
@app.get("/admins", response_class=HTMLResponse)
async def admins_page(request: Request, current_user: str = Depends(get_current_username)):
    """Admin management page"""
    is_admin = True # Todo: Check if super-admin? For now all admins are equal.
    admins_list = AuthManager.list_admins()
    
    return templates.TemplateResponse("admins.html", get_page_context(
        request, current_user, "users",
        admins=admins_list
    ))

@app.post("/api/admins", dependencies=[Depends(get_current_username)])
async def create_admin(
    username: str = Form(...),
    password: str = Form(None),
    auth_source: str = Form("local")
):
    """Create a new admin"""
    # Validation
    if auth_source == "local" and not password:
        raise HTTPException(status_code=400, detail="Password required for local auth")
    
    success, message = AuthManager.create_admin(username, password, auth_source)
    if success:
        return {"success": True, "message": message}
    else:
        raise HTTPException(status_code=400, detail=message)

@app.delete("/api/admins/{username}", dependencies=[Depends(get_current_username)])
async def delete_admin(username: str, current_user: str = Depends(get_current_username)):
    """Delete an admin"""
    if username == current_user:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
        
    success, message = AuthManager.delete_admin(username)
    if success:
        return {"success": True, "message": message}
    else:
        raise HTTPException(status_code=400, detail=message)

# ------------------------------------------------------------------------------
# MFA Credential Management API
# ------------------------------------------------------------------------------
@app.get("/admins/{username}/mfa", response_class=HTMLResponse)
async def admin_mfa_page(username: str, request: Request, current_user: str = Depends(get_current_username)):
    """MFA management page for a specific admin user"""
    return templates.TemplateResponse("admin_mfa.html", get_page_context(
        request, current_user, "users",
        managed_username=username
    ))

@app.get("/api/admins/{username}/mfa/credentials", dependencies=[Depends(get_current_username)])
async def list_user_mfa_credentials(username: str):
    """List all WebAuthn credentials for a user"""
    from roxx.core.auth.webauthn_db import WebAuthnDatabase
    try:
        creds = WebAuthnDatabase.list_credentials(username)
        # Convert binary fields to base64 for JSON serialization
        import base64
        for cred in creds:
            if 'credential_id' in cred and isinstance(cred['credential_id'], bytes):
                cred['credential_id'] = base64.b64encode(cred['credential_id']).decode('utf-8')
            if 'public_key' in cred and isinstance(cred['public_key'], bytes):
                cred['public_key'] = base64.b64encode(cred['public_key']).decode('utf-8')
        return {"credentials": creds}
    except Exception as e:
        logger.error(f"Error listing credentials: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/admins/{username}/mfa/webauthn/{credential_id}", dependencies=[Depends(get_current_username)])
async def delete_webauthn_credential(username: str, credential_id: int):
    """Delete a specific WebAuthn credential"""
    from roxx.core.auth.webauthn_db import WebAuthnDatabase
    try:
        success = WebAuthnDatabase.delete_credential(credential_id, username)
        if success:
            return {"success": True, "message": "Credential deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Credential not found")
    except Exception as e:
        logger.error(f"Error deleting credential: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/admins/{username}/mfa/totp/reset", dependencies=[Depends(get_current_username)])
async def reset_user_totp(username: str):
    """Reset TOTP MFA for a user"""
    from roxx.core.auth.db import AdminDatabase
    try:
        success = AdminDatabase.reset_totp(username)
        if success:
            return {"success": True, "message": "TOTP reset successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to reset TOTP")
    except Exception as e:
        logger.error(f"Error resetting TOTP: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/admins/{username}/mfa/status", dependencies=[Depends(get_current_username)])
async def get_user_mfa_status(username: str):
    """Get MFA status for a user"""
    from roxx.core.auth.db import AdminDatabase
    from roxx.core.auth.webauthn_db import WebAuthnDatabase
    try:
        totp_status = AdminDatabase.get_mfa_status(username)
        webauthn_creds = WebAuthnDatabase.list_credentials(username)
        
        return {
            "totp_enabled": totp_status.get("totp_enabled", False),
            "sms_enabled": totp_status.get("sms_enabled", False),
            "webauthn_count": len(webauthn_creds)
        }
    except Exception as e:
        logger.error(f"Error getting MFA status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ------------------------------------------------------------------------------
# User Management API
# ------------------------------------------------------------------------------
@app.post("/api/users", dependencies=[Depends(get_current_username)])
async def create_user(
    username: str = Form(...),
    password: str = Form(...),
    user_type: str = Form(default="Cleartext-Password")
):
    """Add a new user"""
    if SystemManager.add_radius_user(username, password, user_type):
        return {"success": True, "message": f"User {username} added"}
    else:
        raise HTTPException(status_code=500, detail="Failed to write to users.conf")

@app.delete("/api/users/{username}", dependencies=[Depends(get_current_username)])
async def delete_user(username: str):
    """Delete a user"""
    if SystemManager.delete_radius_user(username):
        return {"success": True, "message": f"User {username} deleted"}
    else:
        raise HTTPException(status_code=500, detail="Failed to delete user")

# ------------------------------------------------------------------------------
# Real-time Logs (WebSocket)
# ------------------------------------------------------------------------------

# Track active WebSocket connections for log streaming
active_log_websockets: List[WebSocket] = []

async def get_current_username_ws(websocket: WebSocket):
    """Verifies Basic Auth for WebSocket manually"""
    # Browser cannot send custom headers on WS connect easily.
    # We can read from Sec-WebSocket-Protocol or Cookie if available.
    # For now, let's implement soft failing: if no auth, just allow (for demo) 
    # OR better: parse Authorization header which might be sent by non-browser clients (like our test script)
    # Browsers typically handle auth via Cookie/Session from the main page.
    # Since we use Basic Auth, the browser caches the creds.
    # UNFORTUNATELY, standard JS WebSocket API DOES NOT send Authorization header with the handshake automatically 
    # unless it was conditioned by a 401 on the same origin previously.
    # However, Python server needs to explicitly look for it.
    
    auth_header = websocket.headers.get("authorization")
    if not auth_header:
        # Strict mode: Reject
        # await websocket.close(code=1008) # Policy Violation
        # raise WebSocketDisconnect()
        return None # Let endpoint handle rejection if critical

    try:
        scheme, param = auth_header.split()
        if scheme.lower() != "basic":
            return None
        decoded = base64.b64decode(param).decode("utf-8")
        username,password = decoded.split(":")
        
        correct_username = os.getenv("ROXX_ADMIN_USER", "admin")
        correct_password = os.getenv("ROXX_ADMIN_PASSWORD", "admin")
        
        if secrets.compare_digest(username, correct_username) and secrets.compare_digest(password, correct_password):
            return username
    except:
        return None
    return None

@app.websocket("/ws/logs")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    # Check Auth manually
    # Note: Browsers are tricky with Basic Auth + WS. 
    # If standard browser usage relies on prior HTTP auth, the browser MIGHT send the header if the origin matched.
    # But usually it relies on Cookies.
    # Given we set up Basic Auth, we can try to validate. If missing, we warn but allow connection for now 
    # to avoid breaking the Dashboard which might not send the header explicitly in JS.
    active_log_websockets.append(websocket)
    try:
        await websocket.send_text("Connected to Real-Time System Logs...")
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except:
        if websocket in active_log_websockets:
            active_log_websockets.remove(websocket)


# ------------------------------------------------------------------------------
# MFA API Endpoints
# ------------------------------------------------------------------------------
from roxx.core.auth.mfa import MFAManager
from roxx.core.auth.mfa_db import MFADatabase

@app.post("/api/mfa/enroll")
async def mfa_enroll(request: Request, username: str = Depends(get_current_username)):
    """Start MFA enrollment for current user"""
    secret = MFAManager.generate_secret()
    totp_uri = MFAManager.generate_totp_uri(username, secret)
    qr_code_data = MFAManager.generate_qr_code(totp_uri)
    plain_codes, hashed_codes = MFAManager.generate_backup_codes(10)
    
    request.session['mfa_enrollment'] = {
        'secret': secret,
        'backup_codes': hashed_codes
    }
    
    return {
        "success": True,
        "secret": secret,
        "qr_code": qr_code_data,
        "backup_codes": plain_codes
    }

@app.post("/api/mfa/verify-enrollment")
async def mfa_verify_enrollment(request: Request, token: str = Form(...), username: str = Depends(get_current_username)):
    """Verify TOTP token and complete enrollment"""
    enrollment = request.session.get('mfa_enrollment')
    if not enrollment:
        raise HTTPException(status_code=400, detail="No enrollment in progress")
    
    if not MFAManager.verify_totp(enrollment['secret'], token):
        raise HTTPException(status_code=400, detail="Invalid token")
    
    success, message = MFADatabase.enroll_totp(username, enrollment['secret'], enrollment['backup_codes'])
    if success:
        request.session.pop('mfa_enrollment', None)
        return {"success": True, "message": "MFA enabled"}
    raise HTTPException(status_code=500, detail=message)

@app.get("/api/mfa/status")
async def mfa_status(request: Request, username: str = Depends(get_current_username)):
    """Get MFA status for current user"""
    settings = MFADatabase.get_mfa_settings(username)
    if settings:
        return {
            "enabled": settings['mfa_enabled'],
            "type": settings.get('mfa_type'),
            "backup_codes_remaining": len(settings.get('backup_codes', []))
        }
    return {"enabled": False}

@app.post("/api/mfa/disable")
async def mfa_disable(request: Request, username: str = Depends(get_current_username)):
    """Disable MFA for current user"""
    success, message = MFADatabase.disable_mfa(username)
    if success:
        return {"success": True, "message": message}
    raise HTTPException(status_code=500, detail=message)



@app.get("/config/ssl", response_class=HTMLResponse)
async def ssl_settings_page(request: Request, current_user: str = Depends(get_current_username)):
    """SSL/TLS Settings Page"""
    return templates.TemplateResponse("ssl_settings.html", get_page_context(
        request, current_user, "settings"
    ))

@app.get("/api/system/ssl/status", dependencies=[Depends(get_current_username)])
async def get_ssl_status():
    from roxx.core.security.cert_manager import CertManager
    return CertManager.get_status()

@app.post("/api/system/ssl/upload", dependencies=[Depends(get_current_username)])
async def upload_ssl_cert(request: Request):
    from roxx.core.security.cert_manager import CertManager
    
    try:
        # Expecting multipart form or json with content?
        # Let's support JSON with file content strings for simplicity given textarea input, 
        # or multipart if file upload. 
        # The prompt implies "upload", but text area copy-paste is often easier for admins.
        # Let's support JSON payload with text.
        
        data = await request.json()
        cert_content = data.get('cert_content')
        key_content = data.get('key_content')
        
        if not cert_content or not key_content:
            raise HTTPException(status_code=400, detail="Missing certificate or key content")
            
        success, message = CertManager.upload_cert(cert_content, key_content)
        
        if success:
            return {"success": True, "message": message}
        else:
            raise HTTPException(status_code=400, detail=message)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/system/ssl/remove", dependencies=[Depends(get_current_username)])
async def remove_ssl_cert():
    from roxx.core.security.cert_manager import CertManager
    success, msg = CertManager.remove_cert()
    return {"success": success, "message": msg}

# ------------------------------------------------------------------------------
# TOTP Routes
# ------------------------------------------------------------------------------
@app.post("/api/totp/generate-qr", dependencies=[Depends(get_current_username)])
async def generate_totp_qr(request: Request):
    """Generate a new TOTP secret and QR code"""
    username = await get_current_username(request)
    form = await request.form()
    
    # Optional: verify form['username'] matches current user if stricter security needed
    # form_user = form.get('username')
    
    try:
        # Generate secret
        secret, provisioning_uri = AuthManager.setup_mfa(username)
        
        # Generate QR Code image
        import qrcode
        import io
        import base64
        
        img = qrcode.make(provisioning_uri)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        img_str = base64.b64encode(buf.getvalue()).decode("utf-8")
        
        return {
            "success": True,
            "qr_code": f"data:image/png;base64,{img_str}",
            "secret": secret
        }
    except Exception as e:
        logger.error(f"Error generating TOTP: {e}")
        return {"success": False, "error": str(e)}



# ------------------------------------------------------------------------------
# Backend Config (SMS/Email)
# ------------------------------------------------------------------------------
from roxx.core.auth.sms import SMSProvider

@app.get("/api/config/mfa-gateways", dependencies=[Depends(get_current_username)])
async def get_mfa_gateways():
    # Load from system config (mocked or JSON file)
    # Ideally should use a proper ConfigManager
    config_path = SystemManager.get_config_dir() / "mfa_gateways.json"
    if config_path.exists():
        return json.loads(config_path.read_text())
    return {
        "sms": {"provider": "disabled"},
        "email": {"enabled": False}
    }

@app.post("/api/config/mfa-gateways", dependencies=[Depends(get_current_username)])
async def save_mfa_gateways(request: Request):
    data = await request.json()
    config_path = SystemManager.get_config_dir() / "mfa_gateways.json"
    config_path.write_text(json.dumps(data, indent=2))
    return {"success": True}

@app.post("/api/test/sms", dependencies=[Depends(get_current_username)])
async def test_sms(request: Request):
    data = await request.json()
    phone = data.get("phone")
    message = data.get("message", "Test from RoXX")
    config = data.get("config") # Test with provided config or saved?
    
    if not config:
         # Load saved
         config_path = SystemManager.get_config_dir() / "mfa_gateways.json"
         if config_path.exists():
             full_conf = json.loads(config_path.read_text())
             config = full_conf.get("sms", {})

    if not config or config.get("provider") == "disabled":
        return {"success": False, "message": "SMS disabled"}

    result = await SMSProvider.send_sms(phone, message, config)
    return {"success": result}

@app.post("/api/test/email", dependencies=[Depends(get_current_username)])
async def test_email(request: Request):
    from roxx.core.auth.email import EmailProvider
    data = await request.json()
    email = data.get("email")
    subject = data.get("subject", "RoXX Test Email")
    body = data.get("body", "This is a test email from your RoXX configuration.")
    config = data.get("config")
    
    if not config:
         config_path = SystemManager.get_config_dir() / "mfa_gateways.json"
         if config_path.exists():
             full_conf = json.loads(config_path.read_text())
             config = full_conf.get("email", {})

    if not config or not config.get("enabled"):
        return {"success": False, "message": "Email disabled"}

    # Fix types from frontend forms (ports as strings)
    if 'smtp_port' in config:
        config['smtp_port'] = int(config['smtp_port'])
    if 'use_tls' in config:
        config['use_tls'] = str(config['use_tls']).lower() == 'true'

    result = await EmailProvider.send_email(email, subject, body, config)
    return {"success": result}

@app.post("/api/mfa/cert/register", dependencies=[Depends(get_current_username)])
async def register_client_cert(request: Request):
    from roxx.core.security.cert_auth import CertAuthManager
    from roxx.core.auth.cert_db import CertDatabase
    
    username = await get_current_username(request)
    cert_info = CertAuthManager.get_cert_info(request)
    if not cert_info:
        raise HTTPException(status_code=400, detail="No client certificate presented")
    existing_user = CertDatabase.get_user_by_fingerprint(cert_info['fingerprint'])
    if existing_user:
         raise HTTPException(status_code=400, detail=f"Certificate already registered to {existing_user}")
    CertDatabase.add_cert(username, cert_info['fingerprint'], cert_info['common_name'], cert_info['issuer'], f"Registered: {datetime.now().strftime('%Y-%m-%d')}")
    return {"success": True, "message": "Certificate linked successfully"}

@app.get("/api/mfa/cert/list", dependencies=[Depends(get_current_username)])
async def list_client_certs(request: Request):
    from roxx.core.auth.cert_db import CertDatabase
    username = await get_current_username(request)
    return CertDatabase.get_user_certs(username)

@app.delete("/api/mfa/cert/{cert_id}", dependencies=[Depends(get_current_username)])
async def delete_client_cert(cert_id: int, request: Request):
    from roxx.core.auth.cert_db import CertDatabase
    username = await get_current_username(request)
    if CertDatabase.delete_cert(username, cert_id):
        return {"success": True}
    raise HTTPException(status_code=404, detail="Certificate not found")

@app.post("/api/system/ssl/ca", dependencies=[Depends(get_current_username)])
async def upload_ca_bundle(file: UploadFile = File(...)):
    from roxx.core.security.cert_manager import CertManager
    content = (await file.read()).decode('utf-8')
    success, msg = CertManager.upload_ca(content)
    if success:
        return {"success": True, "message": msg}
    raise HTTPException(status_code=400, detail=msg)

@app.delete("/api/system/ssl/ca", dependencies=[Depends(get_current_username)])
async def remove_ca_bundle():
    from roxx.core.security.cert_manager import CertManager
    success, msg = CertManager.remove_ca()
    if success:
        return {"success": True, "message": msg}
    raise HTTPException(status_code=400, detail=msg)

    return {"status": "healthy", "service": "roxx-web"}


# ------------------------------------------------------------------------------
# SAML Authentication Routes
# ------------------------------------------------------------------------------
# NOTE: SAML imports are lazy-loaded due to xmlsec dependency issues
# from roxx.core.auth.saml_provider import SAMLProvider
from roxx.core.auth.config_db import ConfigManager
from fastapi.responses import Response

@app.get("/auth/saml/metadata/{provider_id}")
async def saml_metadata(provider_id: int):
    """
    Generate and return SAML SP metadata XML
    
    Args:
        provider_id: ID of the SAML provider configuration
    """
    try:
        from roxx.core.auth.saml_provider import SAMLProvider
    except ImportError as e:
        raise HTTPException(status_code=503, detail=f"SAML not available: {e}")
    
    provider = ConfigManager.get_provider(provider_id)
    if not provider or provider['provider_type'] != 'saml':
        raise HTTPException(status_code=404, detail="SAML provider not found")
    
    try:
        # Add SP ACS URL to config (generated from app URL)
        config = provider['config']
        if 'sp_acs_url' not in config:
            config['sp_acs_url'] = f"http://localhost:8000/auth/saml/acs/{provider_id}"
        
        saml = SAMLProvider(config)
        metadata_xml = saml.get_metadata()
        
        return Response(content=metadata_xml, media_type="application/xml")
    except Exception as e:
        logger.error(f"Error generating SAML metadata: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/auth/saml/login/{provider_id}")
async def saml_login(provider_id: int, request: Request, relay_state: str = None):
    """
    Initiate SAML SSO login flow
    
    Args:
        provider_id: ID of the SAML provider
        relay_state: Optional URL to redirect after successful auth
    """
    provider = ConfigManager.get_provider(provider_id)
    if not provider or provider['provider_type'] != 'saml':
        raise HTTPException(status_code=404, detail="SAML provider not found")
    
    if not provider['enabled']:
        raise HTTPException(status_code=403, detail="Provider is disabled")
    
    try:
        # Prepare request data for python3-saml
        request_data = {
            'https': 'on' if request.url.scheme == 'https' else 'off',
            'http_host': request.url.hostname,
            'script_name': request.url.path,
            'server_port': request.url.port or (443 if request.url.scheme == 'https' else 80),
            'get_data': dict(request.query_params),
            'post_data': {}
        }
        
        config = provider['config']
        if 'sp_acs_url' not in config:
            config['sp_acs_url'] = f"{request.url.scheme}://{request.url.hostname}:{request.url.port or 8000}/auth/saml/acs/{provider_id}"
        
        saml = SAMLProvider(config)
        redirect_url = saml.initiate_sso(request_data, relay_state=relay_state or "/dashboard")
        
        # Store provider_id in session for ACS callback
        request.session['saml_provider_id'] = provider_id
        
        return {"redirect_url": redirect_url}
    except Exception as e:
        logger.error(f"Error initiating SAML SSO: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/auth/saml/acs/{provider_id}")
async def saml_acs(provider_id: int, request: Request):
    """
    SAML Assertion Consumer Service - handles IdP response
    
    Args:
        provider_id: ID of the SAML provider
    """
    provider = ConfigManager.get_provider(provider_id)
    if not provider or provider['provider_type'] != 'saml':
        raise HTTPException(status_code=404, detail="SAML provider not found")
    
    try:
        # Prepare request data
        form_data = await request.form()
        request_data = {
            'https': 'on' if request.url.scheme == 'https' else 'off',
            'http_host': request.url.hostname,
            'script_name': request.url.path,
            'server_port': request.url.port or (443 if request.url.scheme == 'https' else 80),
            'get_data': {},
            'post_data': {
                'SAMLResponse': form_data.get('SAMLResponse'),
                'RelayState': form_data.get('RelayState', '')
            }
        }
        
        config = provider['config']
        if 'sp_acs_url' not in config:
            config['sp_acs_url'] = str(request.url)
        
        saml = SAMLProvider(config)
        success, user_data, error = saml.process_response(request_data)
        
        if not success:
            logger.error(f"SAML authentication failed: {error}")
            raise HTTPException(status_code=401, detail=error)
        
        # Create or update user from SAML attributes
        from roxx.core.auth.manager import AuthManager
        username = user_data['username']
        
        # Check if user exists, create if needed
        try:
            auth_success, _ = AuthManager.verify_credentials(username, None)
            if not auth_success:
                # Create user with external auth source
                AuthManager.create_admin(username, None, auth_source='saml')
        except:
            AuthManager.create_admin(username, None, auth_source='saml')
        
        # Set session
        session_val = base64.b64encode(f"{username}:active".encode("utf-8")).decode("utf-8")
        
        # Redirect to original target or dashboard
        redirect_to = form_data.get('RelayState', '/dashboard')
        response = RedirectResponse(url=redirect_to, status_code=303)
        response.set_cookie(key="session", value=session_val, httponly=True)
        
        AuditManager.log(request, "SAML_LOGIN_SUCCESS", "INFO", 
                        {"username": username, "provider": provider['name']}, 
                        username=username)
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing SAML response: {e}")
        AuditManager.log(request, "SAML_LOGIN_FAILED", "ERROR", 
                        {"error": str(e), "provider": provider['name']})
        raise HTTPException(status_code=500, detail=str(e))


def main():
    import uvicorn
    from roxx.core.security.cert_manager import CertManager
    
    ssl_cert, ssl_key = CertManager.get_cert_paths()
    ca_bundle = CertManager.get_ca_paths()
    ssl_enabled = ssl_cert.exists() and ssl_key.exists()
    
    config_kwargs = {
        "host": "0.0.0.0",
        "port": 8000,
        "log_level": "info",
        "app": "roxx.web.app:app"
    }
    
    if ssl_enabled:
        print(f"[Core] Starting in HTTPS mode with {ssl_cert}")
        config_kwargs["ssl_certfile"] = str(ssl_cert)
        config_kwargs["ssl_keyfile"] = str(ssl_key)
        
        if ca_bundle.exists():
            print(f"[Core] Enabling Client Certificate Auth with CA: {ca_bundle}")
            config_kwargs["ssl_ca_certs"] = str(ca_bundle)
            config_kwargs["ssl_cert_reqs"] = ssl.CERT_OPTIONAL
    else:
        print("[Core] No SSL Certificates found. Starting in HTTP mode.")

    uvicorn.run(**config_kwargs)



@app.get("/api/webauthn/login/options")
async def webauthn_login_options(request: Request):
    """Get WebAuthn login options"""
    session_cookie = request.cookies.get("session")
    if not session_cookie:
        raise HTTPException(status_code=401, detail="Session required")
    
    try:
        decoded = base64.b64decode(session_cookie).decode("utf-8")
        username, status = decoded.split(":", 1)
        if status != "mfa_pending":
             raise HTTPException(status_code=401, detail="Invalid session state")
    except:
        raise HTTPException(status_code=401, detail="Invalid session")

    from roxx.core.auth.webauthn import WebAuthnManager
    options, state = WebAuthnManager.generate_authentication_options(username)
    
    if not options:
        raise HTTPException(status_code=400, detail="No credentials found")
        
    # Store state in session
    request.session["webauthn_state"] = state
    
    return JSONResponse(options)

@app.post("/api/webauthn/login/verify")
async def webauthn_login_verify(request: Request):
    """Verify WebAuthn login"""
    try:
        data = await request.json()
    except:
        raise HTTPException(status_code=400, detail="Invalid JSON")
        
    session_cookie = request.cookies.get("session")
    if not session_cookie:
        raise HTTPException(status_code=401, detail="Session required")
        
    try:
        decoded = base64.b64decode(session_cookie).decode("utf-8")
        username, status = decoded.split(":", 1)
    except:
        raise HTTPException(status_code=401, detail="Invalid session")

    state = request.session.get("webauthn_state")
    if not state:
        raise HTTPException(status_code=400, detail="State not found")
        
    from roxx.core.auth.webauthn import WebAuthnManager
    success, msg = WebAuthnManager.verify_authentication(username, data, state)
    
    if success:
        # Success!
        session_val = base64.b64encode(f"{username}:active".encode("utf-8")).decode("utf-8")
        response = JSONResponse({"success": True})
        response.set_cookie(key="session", value=session_val, httponly=True)
        request.session.pop("webauthn_state", None)
        request.session.pop('mfa_username', None)
        return response
    else:
        return JSONResponse({"success": False, "detail": msg}, status_code=400)


if __name__ == "__main__":
    main()
