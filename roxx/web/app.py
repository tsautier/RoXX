"""
RoXX Web Interface - Modern FastAPI Application
Replaces the old SimpleSAMLphp interface with a modern Python web app
"""

from fastapi import FastAPI, Request, Form, HTTPException, Depends, WebSocket, WebSocketDisconnect, UploadFile, File
from contextlib import asynccontextmanager
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
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
import json
import ssl
import sqlite3
import random
import re
from datetime import datetime
from pathlib import Path
from typing import List

from roxx.core.auth.totp import TOTPAuthenticator
from roxx.utils.system import SystemManager
from roxx.core.auth.saml_provider import SAMLProvider
from roxx.core.auth.rbac import (
    Role,
    Action,
    require_role,
    require_action,
    get_role_from_session,
    get_auth_context,
    set_auth_context,
    clear_auth_context,
)

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

VERSION = "1.0.0-beta9"

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Modern Lifespan context manager for startup and shutdown events.
    Replaces the deprecated @app.on_event system.
    """
    # 🏁 Startup Logic
    from roxx.core.auth.webauthn import WebAuthnManager
    from roxx.core.auth.cert_db import CertDatabase
    from roxx.core.integrity import IntegrityManager
    
    WebAuthnManager.init()
    CertDatabase.init_db()
    
    # 🛡️ Integrity Check on Startup
    # In a production build, the expected_manifest would be signed and baked into the binary.
    # For this phase, we generate it to ensure we start from a known good state.
    known_good = IntegrityManager.generate_manifest()
    # Log manifest generation for audit
    logger.info(f"[Integrity] Manifest generated for {len(known_good)} core files.")
    
    # Verify initial state
    violations = IntegrityManager.verify_integrity(known_good)
    modified = [v['path'] for v in violations if v['status'] != 'OK']
    if modified:
        logger.warning(f"[Integrity] Startup verification failed for: {modified}")
    else:
        logger.info("[Integrity] Startup verification successful. All core files match manifest.")

    yield
    # 🛑 Shutdown Logic (if any)
    logger.info("Cleaning up resources on shutdown...")

app = FastAPI(
    title="RoXX Admin Interface",
    description="Modern web interface for RoXX RADIUS Authentication Proxy",
    version=VERSION,
    lifespan=lifespan
)

# Initialize Rate Limiter
app.state.limiter = limiter

@app.middleware("http")
async def add_integrity_headers(request: Request, call_next):
    """Adds ownership and integrity headers to protect against dishonest clones"""
    response = await call_next(request)
    response.headers["X-RoXX-Origin"] = "Built with Love by tsautier"
    response.headers["X-RoXX-Build-ID"] = "ST-2026-BETA9-DRAFT-01"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Developed-For"] = "SH-PX Framework (Confidential)"
    return response

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
    return templates.TemplateResponse(request, "429.html", {"request": request}, status_code=429)

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
from roxx.core.auth.db import AdminDatabase

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
    Also extracts role from cookie.
    """
    auth = get_auth_context(request)
    if auth and auth.get("username") and auth.get("status") == "active":
        return auth["username"]

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


def _rethrow_http_exception(exc: Exception) -> None:
    if isinstance(exc, HTTPException):
        raise exc


def _load_mfa_gateway_config() -> dict:
    config_path = SystemManager.get_config_dir() / "mfa_gateways.json"
    if not config_path.exists():
        return {"sms": {"provider": "disabled"}, "email": {"enabled": False}}
    try:
        return json.loads(config_path.read_text())
    except Exception:
        logger.exception("Failed to read MFA gateway configuration")
        return {"sms": {"provider": "disabled"}, "email": {"enabled": False}}


def _get_sms_gateway_config() -> dict:
    return _load_mfa_gateway_config().get("sms", {})


def _is_sms_gateway_enabled() -> bool:
    config = _get_sms_gateway_config()
    return bool(config) and config.get("provider") not in (None, "", "disabled")


async def _send_sms_login_code(request: Request, username: str) -> str:
    phone_number = AdminDatabase.get_phone_number(username)
    if not phone_number:
        raise HTTPException(status_code=400, detail="No phone number configured")

    if not _is_sms_gateway_enabled():
        raise HTTPException(status_code=400, detail="SMS gateway is disabled")

    code = f"{random.randint(0, 999999):06d}"
    request.session["mfa_code_sms"] = code
    sent = await SMSProvider.send_sms(
        phone_number,
        f"Your RoXX code is {code}",
        _get_sms_gateway_config(),
    )
    if not sent:
        request.session.pop("mfa_code_sms", None)
        raise HTTPException(status_code=502, detail="Failed to send SMS code")
    return phone_number

# Dependency for Auth Routes (allows partial auth)
async def get_partial_user(request: Request):
    auth = get_auth_context(request)
    if auth:
        return auth.get("username"), auth.get("status")
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
    return templates.TemplateResponse(request, "login.html", {"request": request})

@app.post("/login")
@limiter.limit("5/minute")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    # Verify credentials
    success, user_data = AuthManager.verify_credentials(username, password)
    
    if success:
        # Check Force Change Password
        if user_data.get("must_change_password"):
            set_auth_context(request, username, "force_change")
            response = JSONResponse({"success": True, "redirect": "/auth/change-password"})
            response.delete_cookie("session")
            return response

        # Discovery MFA Methods
        mfa_methods = []
        
        # 1. TOTP / Email (from MFADatabase)
        mfa_settings = MFADatabase.get_mfa_settings(username) or {}
        if mfa_settings.get('mfa_enabled'):
            # Current DB schema 'mfa_type' is single, but let's be robust
            m_type = mfa_settings.get('mfa_type', 'totp')
            mfa_methods.append(m_type)

        # 1b. SMS can coexist as a self-service factor backed by the admin profile
        if AdminDatabase.get_phone_number(username) and _is_sms_gateway_enabled():
            if 'sms' not in mfa_methods:
                mfa_methods.append('sms')
            
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
                        set_auth_context(request, username, "active")
                        response = JSONResponse({"success": True, "redirect": "/"})
                        response.delete_cookie("session")
                        AuditManager.log(request, "LOGIN_SUCCESS", "INFO", {"username": username, "method": "trusted_device"}, username=username)
                        return response
                except: pass

            # MFA Required
            request.session['mfa_username'] = username # Store for verification steps
            set_auth_context(request, username, "mfa_pending")
            
            response = JSONResponse({
                "success": True,
                "mfa_required": True,
                "username": username,
                "mfa_methods": mfa_methods
            })
            response.delete_cookie("session")
            AuditManager.log(request, "LOGIN_MFA_REQUIRED", "INFO", {"username": username, "mfa_methods": mfa_methods}, username=username)
            return response

        # No MFA - Login
        user_role = set_auth_context(request, username, "active")["role"]
        response = JSONResponse({"success": True, "redirect": "/dashboard"})
        response.delete_cookie("session")
        AuditManager.log(request, "LOGIN_SUCCESS", "INFO", {"username": username, "method": "password_only", "role": user_role}, username=username)
        return response
    
    AuditManager.log(request, "LOGIN_FAILED", "WARNING", {"username": username, "reason": "invalid_credentials"}, username=username)
    return JSONResponse(status_code=401, content={"success": False, "detail": "Invalid credentials"})


@app.get("/logout")
async def logout(request: Request):
    response = RedirectResponse(url="/login")
    response.delete_cookie("session")
    response.delete_cookie("roxx_session")
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
    auth = get_auth_context(request)
    if not auth or auth.get("status") != "mfa_pending":
        return RedirectResponse(url="/login", status_code=303)
    
    return templates.TemplateResponse(request, "mfa_verify.html", {
        "request": request,
        "username": auth["username"]
    })

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
    auth = get_auth_context(request)
    if not auth or auth.get("status") != "mfa_pending":
        raise HTTPException(status_code=401, detail="Invalid session")
    username = auth["username"]

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
        set_auth_context(request, username, "active")
        response = JSONResponse({"success": True})
        response.delete_cookie("session")
        
        # Cleanup
        request.session.pop('mfa_username', None)
        
        AuditManager.log(request, "MFA_SUCCESS", "INFO", {"username": username, "method": mfa_type}, username=username)
        return response

    AuditManager.log(request, "MFA_FAILED", "WARNING", {"username": username, "method": mfa_type, "reason": "invalid_code"}, username=username)
    return JSONResponse({"success": False, "detail": "Invalid Code"}, status_code=400)


@app.post("/auth/mfa/send-otp")
@limiter.limit("5/minute")
async def send_mfa_otp(request: Request):
    """Send a login OTP for SMS-based MFA."""
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    auth = get_auth_context(request)
    if not auth or auth.get("status") != "mfa_pending":
        raise HTTPException(status_code=401, detail="Invalid session")

    if data.get("type") != "sms":
        raise HTTPException(status_code=400, detail="Unsupported MFA type")

    phone_number = await _send_sms_login_code(request, auth["username"])
    masked_phone = f"...{phone_number[-4:]}" if len(phone_number) >= 4 else phone_number
    AuditManager.log(
        request,
        "MFA_OTP_SENT",
        "INFO",
        {"username": auth["username"], "method": "sms"},
        username=auth["username"],
    )
    return {"success": True, "message": f"SMS code sent to {masked_phone}"}

@app.post("/auth/mfa/cert/verify")
async def mfa_cert_verify(request: Request):
    """Verify Client Certificate for MFA"""
    # ... (Session Check as above) ...
    # Verify Cert
    from roxx.core.security.cert_auth import CertAuthManager
    from roxx.core.auth.cert_db import CertDatabase
    
    auth = get_auth_context(request)
    if not auth or auth.get("status") != "mfa_pending":
        return JSONResponse({"success": False, "detail": "Session Error"}, status_code=401)
    username = auth["username"]

    cert_info = CertAuthManager.get_cert_info(request)
    if not cert_info:
         return JSONResponse({"success": False, "detail": "No Certificate"}, status_code=400)
    
    # Check if this cert is registered to this user
    stored_user = CertDatabase.get_user_by_fingerprint(cert_info['fingerprint'])
    
    if stored_user and stored_user == username:
        set_auth_context(request, username, "active")
        response = JSONResponse({"success": True})
        response.delete_cookie("session")
        AuditManager.log(request, "MFA_SUCCESS", "INFO", {"username": username, "method": "client_cert", "fingerprint": cert_info['fingerprint']}, username=username)
        return response
        
    AuditManager.log(request, "MFA_FAILED", "WARNING", {"username": username, "method": "client_cert", "reason": "cert_mismatch", "fingerprint": cert_info['fingerprint']}, username=username)
    return JSONResponse({"success": False, "detail": "Certificate not linked to user"}, status_code=403)


# ------------------------------------------------------------------------------
# Password & MFA Management
# ------------------------------------------------------------------------------
@app.get("/auth/change-password", response_class=HTMLResponse)
async def change_password_page(request: Request):
    """Change Password Page"""
    username, status = await get_partial_user(request)
    if not username or status not in ['active', 'force_change']:
        return RedirectResponse("/login")
        
    return templates.TemplateResponse(request, "change_password.html", get_page_context(
        request, username, "password"
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
        return templates.TemplateResponse(request, "change_password.html", {
            "request": request, "error": "New passwords do not match"
        })

    success, _ = AuthManager.verify_credentials(username, current_password)
    if not success:
        return templates.TemplateResponse(request, "change_password.html", {
            "request": request, "error": "Current password incorrect"
        })

    try:
        AuthManager.change_password(username, new_password)
    except ValueError as e:
         return templates.TemplateResponse(request, "change_password.html", {
            "request": request, "error": str(e)
        })

    # Success -> Active Session
    set_auth_context(request, username, "active")
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("session")
    return response

@app.get("/auth/mfa-challenge", response_class=HTMLResponse)
async def mfa_challenge_page(request: Request):
    username, status = await get_partial_user(request)
    if not username or status != "mfa_pending":
        return RedirectResponse("/login")
    return templates.TemplateResponse(request, "mfa_challenge.html", {"request": request})

@app.post("/auth/mfa-challenge", response_class=HTMLResponse)
async def mfa_challenge(request: Request, code: str = Form(...)):
    username, status = await get_partial_user(request)
    if not username or status != "mfa_pending":
        return RedirectResponse("/login")

    if AuthManager.verify_mfa(username, code):
        set_auth_context(request, username, "active")
        response = RedirectResponse(url="/", status_code=303)
        response.delete_cookie("session")
        return response
    
    return templates.TemplateResponse(request, "mfa_challenge.html", {
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
    
    return templates.TemplateResponse(request, "mfa_setup.html", {
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
    return templates.TemplateResponse(request, "error.html", {"request": request, "message": "Invalid code. MFA Setup Failed."}) # Needs error.html or logic


# ------------------------------------------------------------------------------
# WebAuthn Routes
# ------------------------------------------------------------------------------
from roxx.core.auth.webauthn import WebAuthnManager
from fido2.utils import websafe_encode, websafe_decode



@app.get("/api/webauthn/authenticate/options")
async def webauthn_auth_options(request: Request):
    """Generate auth options"""
    auth = get_auth_context(request)
    username = auth.get("username") if auth else None
    
    if not username:
        username = request.session.get('mfa_username')

    if not username:
        raise HTTPException(status_code=400, detail="User context missing")
        
    options, state = WebAuthnManager.generate_authentication_options(username, rp_id=request.url.hostname)
    if not options:
         raise HTTPException(status_code=400, detail="No keys found")
         
    request.session["webauthn_auth_state"] = state
    return dict(options)

@app.post("/api/webauthn/authenticate/verify")
async def webauthn_auth_verify(request: Request):
    """Verify auth response"""
    state = request.session.get("webauthn_auth_state")
    auth = get_auth_context(request)
    username = auth.get("username") if auth else None
    if not username:
        username = request.session.get('mfa_username')
        
    if not state or not username:
        raise HTTPException(status_code=400, detail="State or User missing")
        
    data = await request.json()
    success, msg = WebAuthnManager.verify_authentication(username, data, state, rp_id=request.url.hostname)
    
    if success:
        if request.session.get('mfa_username'):
             set_auth_context(request, username, "active")
             response = JSONResponse({"success": True, "redirect": "/"})
             response.delete_cookie("session")
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
    user_role = get_role_from_session(request) or 'admin'
    context = {
        "request": request,
        "username": username,
        "active_page": active_page,
        "version": VERSION,
        "user_role": user_role,
        **kwargs
    }
    return context


def get_system_settings_snapshot() -> dict:
    """Return system settings merged with sane defaults."""
    from roxx.core.auth.config_db import ConfigManager

    defaults = {
        "server_name": "RoXX RADIUS Proxy",
        "radius_auth_port": "1812",
        "radius_acct_port": "1813",
        "debug_mode": "false",
        "log_level": "INFO",
        "audit_retention_days": "90",
    }
    return {**defaults, **ConfigManager.get_system_settings()}


def normalize_system_settings_payload(data: dict) -> dict:
    """Normalize incoming system settings payloads from JSON or form data."""
    return {
        "server_name": str(data.get("server_name", "RoXX RADIUS Proxy")).strip() or "RoXX RADIUS Proxy",
        "radius_auth_port": str(data.get("radius_auth_port", "1812")).strip() or "1812",
        "radius_acct_port": str(data.get("radius_acct_port", "1813")).strip() or "1813",
        "log_level": str(data.get("log_level", "INFO")).strip().upper() or "INFO",
        "audit_retention_days": str(data.get("audit_retention_days", "90")).strip() or "90",
        "debug_mode": "true" if str(data.get("debug_mode", "false")).lower() in {"true", "1", "yes", "on"} else "false",
    }

@app.get("/logs-view", response_class=HTMLResponse, dependencies=[Depends(require_action(Action.VIEW_LOGS))])
async def logs_view_page(request: Request, current_user: str = Depends(get_current_username)):
    """Legacy logs route kept as redirect to the canonical page."""
    return RedirectResponse(url="/logs", status_code=303)

@app.get("/", response_class=HTMLResponse, dependencies=[Depends(get_current_username)])
async def home(request: Request):
    """Home page - redirects to dashboard"""
    return RedirectResponse("/dashboard")


@app.get("/totp/enroll", response_class=HTMLResponse, dependencies=[Depends(get_current_username)])
async def totp_enroll_page(request: Request, current_user: str = Depends(get_current_username)):
    """TOTP enrollment page"""
    return templates.TemplateResponse(request, "totp_enroll.html", get_page_context(
        request, current_user, "mfa",
        title="TOTP Enrollment"
    ))

@app.get("/config/mfa-gateways", response_class=HTMLResponse, dependencies=[Depends(require_action(Action.MANAGE_MFA))])
async def config_mfa_gateways_page(request: Request, current_user: str = Depends(get_current_username)):
    """MFA Gateways Configuration Page"""
    return templates.TemplateResponse(request, "config_mfa_gateways.html", get_page_context(
        request, current_user, "config",
        title="MFA Gateways"
    ))

@app.get("/nps-migration", response_class=HTMLResponse, dependencies=[Depends(require_action(Action.MANAGE_RADIUS_CLIENTS))])
async def nps_migration_page(request: Request, current_user: str = Depends(get_current_username)):
    """Legacy alias kept for backwards compatibility."""
    return RedirectResponse(url="/config/nps-migration", status_code=303)

@app.post("/api/nps/analyze", dependencies=[Depends(require_action(Action.MANAGE_RADIUS_CLIENTS))])
async def api_nps_analyze(request: Request, file: UploadFile = File(...)):
    """API to analyze NPS XML file"""
    try:
        content = await file.read()
        from roxx.utils.nps_importer import NPSImporter
        results = NPSImporter.parse_xml(content.decode("utf-8"))
        
        # Mask secrets for UI display
        masked_results = {
            "clients": [
                {**c, "shared_secret": "***" if c["shared_secret"] else ""} 
                for c in results["clients"]
            ],
            "remote_radius_servers": results["remote_radius_servers"]
        }
        
        # Store original results in session for the actual import call
        # (Alternatively, could pass back and forth but session is safer for secrets)
        request.session["nps_import_buffer"] = results
        
        return {"success": True, "results": masked_results}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/nps/import", dependencies=[Depends(require_action(Action.MANAGE_RADIUS_CLIENTS))])
async def api_nps_import(request: Request):
    """API to actually import the analyzed data"""
    buffered_data = request.session.get("nps_import_buffer")
    if not buffered_data:
        raise HTTPException(status_code=400, detail="No analyzed data found in session. Please analyze first.")

    selection = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
    selected_clients = set(selection.get("selected_clients", []))
    selected_servers = set(selection.get("selected_servers", []))
    
    from roxx.core.radius_backends.config_db import RadiusBackendDB
    
    import_count = 0
    # Import Clients
    for client in buffered_data.get("clients", []):
        client_key = f"{client['name']}|{client['address']}"
        if selected_clients and client_key not in selected_clients:
            continue
        success = RadiusBackendDB.add_client(
            shortname=client["name"].lower().replace(" ", "_"),
            ipaddr=client["address"],
            secret=client["shared_secret"],
            description="Imported from NPS"
        )
        if success: import_count += 1
    
    # Import Remote Servers as RADIUS Backends
    imported_backends = 0
    for server in buffered_data.get("remote_radius_servers", []):
        server_key = f"{server['group']}|{server['address']}"
        if selected_servers and server_key not in selected_servers:
            continue
        name = f"NPS_{server['group']}_{server['address']}".replace(".", "_")
        success, _, _ = RadiusBackendDB.create_backend(
            backend_type='radius_server',
            name=name,
            config={"server": server["address"], "port": 1812, "secret": "TODO_MANUAL_INPUT"},
            enabled=True,
            priority=200 # Lower priority for imported servers
        )
        if success:
            imported_backends += 1
        
    # Clear buffer
    del request.session["nps_import_buffer"]
    
    return {"success": True, "message": f"Successfully imported {import_count} clients and {imported_backends} backend stubs."}

@app.get("/api/health/backends", dependencies=[Depends(require_action(Action.VIEW_SYSTEM_INFO))])
async def get_backend_health():
    """Returns actual status of authentication backends"""
    from roxx.core.health import HealthManager
    return await HealthManager.get_backend_status()

@app.get("/api/metrics/auth", dependencies=[Depends(require_action(Action.VIEW_DASHBOARD))])
async def get_auth_metrics(period_hours: int = 24, granularity: str = "hour"):
    """
    Returns authentication success/failure metrics for the selected time window.
    """
    from roxx.core.audit.db import AuditDatabase
    from collections import defaultdict

    if period_hours not in (1, 24):
        raise HTTPException(status_code=400, detail="Unsupported period_hours")
    if granularity not in ("hour", "minute"):
        raise HTTPException(status_code=400, detail="Unsupported granularity")

    conn = AuditDatabase.get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    now = datetime.now()
    if granularity == "hour":
        bucket_delta = timedelta(hours=1)
        bucket_count = period_hours
        start_time = now - timedelta(hours=period_hours - 1)
        first_bucket = start_time.replace(minute=0, second=0, microsecond=0)
        category_format = "%Y-%m-%dT%H:00:00"
    else:
        bucket_delta = timedelta(minutes=1)
        bucket_count = 60 if period_hours == 1 else 24 * 60
        start_time = now - timedelta(minutes=bucket_count - 1)
        first_bucket = start_time.replace(second=0, microsecond=0)
        category_format = "%Y-%m-%dT%H:%M:00"

    buckets = []
    current_bucket = first_bucket
    for _ in range(bucket_count):
        buckets.append(current_bucket)
        current_bucket += bucket_delta

    success_counts = defaultdict(int)
    failure_counts = defaultdict(int)

    try:
        cursor.execute(
            """
            SELECT timestamp, action
            FROM audit_logs
            WHERE action IN ('LOGIN_SUCCESS', 'LOGIN_FAILED')
              AND timestamp >= ?
            ORDER BY timestamp ASC
            """,
            (start_time.strftime("%Y-%m-%d %H:%M:%S"),)
        )

        for row in cursor.fetchall():
            try:
                event_time = datetime.fromisoformat(str(row["timestamp"]))
            except ValueError:
                continue

            if granularity == "hour":
                bucket = event_time.replace(minute=0, second=0, microsecond=0)
            else:
                bucket = event_time.replace(second=0, microsecond=0)

            if bucket < buckets[0] or bucket > buckets[-1]:
                continue

            if row["action"] == "LOGIN_SUCCESS":
                success_counts[bucket] += 1
            elif row["action"] == "LOGIN_FAILED":
                failure_counts[bucket] += 1
    finally:
        conn.close()

    return {
        "success": [success_counts[bucket] for bucket in buckets],
        "failure": [failure_counts[bucket] for bucket in buckets],
        "categories": [bucket.strftime(category_format) for bucket in buckets],
        "period_hours": period_hours,
        "granularity": granularity,
    }

from datetime import timedelta

# ... (API endpoints remain unchanged) ...

@app.get("/dashboard", response_class=HTMLResponse, dependencies=[Depends(require_action(Action.VIEW_DASHBOARD))])
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
    
    return templates.TemplateResponse(request, "dashboard.html", get_page_context(
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


@app.get("/users", response_class=HTMLResponse, dependencies=[Depends(require_action(Action.MANAGE_RADIUS_USERS))])
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
        
    return templates.TemplateResponse(request, "users.html", get_page_context(
        request, current_user, "users",
        users=users_list or ["admin (demo)"]
    ))


@app.get("/api/users", dependencies=[Depends(require_action(Action.MANAGE_RADIUS_USERS))])
async def get_radius_users():
    """List local RADIUS users from users.conf."""
    users_file = SystemManager.get_config_dir() / "users.conf"
    users = []
    if users_file.exists():
        with open(users_file, "r") as f:
            for line in f:
                stripped = line.strip()
                if not stripped or stripped.startswith('#'):
                    continue
                parts = stripped.split()
                if len(parts) >= 4:
                    users.append({
                        "username": parts[0],
                        "attribute": parts[1],
                        "op": parts[2],
                        "password": parts[3].strip('"')
                    })
    return users


@app.post("/api/users", dependencies=[Depends(require_action(Action.MANAGE_RADIUS_USERS))])
async def add_radius_user(request: Request):
    data = await request.json()
    username = data.get("username")
    password = data.get("password")
    if SystemManager.add_radius_user(username, password):
        return {"success": True}
    return {"success": False}


@app.delete("/api/users/{username}", dependencies=[Depends(require_action(Action.MANAGE_RADIUS_USERS))])
async def delete_radius_user(username: str):
    if SystemManager.delete_radius_user(username):
        return {"success": True}
    return {"success": False}


@app.get("/config", response_class=HTMLResponse, dependencies=[Depends(require_action(Action.MANAGE_SYSTEM_CONFIG))])
async def config_page(request: Request, current_user: str = Depends(get_current_username)):
    """Configuration page"""
    return templates.TemplateResponse(request, "config.html", get_page_context(
        request, current_user, "settings"
    ))

@app.get("/config/api-tokens", response_class=HTMLResponse, dependencies=[Depends(require_action(Action.MANAGE_API_TOKENS))])
async def api_tokens_page(request: Request, current_user: str = Depends(get_current_username)):
    """API Tokens Management"""
    return templates.TemplateResponse(request, "api_tokens.html", get_page_context(
        request, current_user, "tokens"
    ))

@app.get("/settings/mfa", response_class=HTMLResponse, dependencies=[Depends(get_current_username)])
async def mfa_settings_page(request: Request, current_user: str = Depends(get_current_username)):
    """MFA Settings Page"""
    return templates.TemplateResponse(request, "mfa_settings.html", get_page_context(
        request, current_user, "mfa"
    ))


# ------------------------------------------------------------------------------
# Authentication Provider Configuration
# ------------------------------------------------------------------------------
@app.get("/config/auth-providers", response_class=HTMLResponse, dependencies=[Depends(require_action(Action.MANAGE_AUTH_PROVIDERS))])
async def auth_providers_page(request: Request, current_user: str = Depends(get_current_username)):
    """Authentication providers configuration page"""
    return templates.TemplateResponse(request, "auth_providers.html", get_page_context(
        request, current_user, "settings"
    ))

@app.get("/config/auth-providers/logs", response_class=HTMLResponse, dependencies=[Depends(require_action(Action.MANAGE_AUTH_PROVIDERS))])
async def auth_providers_logs_page(request: Request, current_user: str = Depends(get_current_username)):
    """Authentication Provider Debug Logs"""
    return templates.TemplateResponse(request, "auth_providers_logs.html", get_page_context(
        request, current_user, "settings"
    ))

@app.get("/api/auth-providers", dependencies=[Depends(require_action(Action.MANAGE_AUTH_PROVIDERS))])
async def list_auth_providers():
    """List all authentication providers"""
    from roxx.core.auth.config_db import ConfigManager
    try:
        ConfigManager.init()  # Ensure DB is initialized
        providers = ConfigManager.list_providers()
        return providers
    except Exception as e:
        _rethrow_http_exception(e)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sys/integrity", dependencies=[Depends(require_action(Action.VIEW_SYSTEM_INFO))])
async def check_integrity():
    """Hidden integrity check for the owner"""
    from roxx.core.integrity import IntegrityManager
    return {"status": "OK", "checksums": IntegrityManager.generate_manifest()}

@app.get("/who-is-the-king", dependencies=[Depends(get_current_username)])
async def crown_jewel():
    """Hidden easter egg to prove ownership"""
    return HTMLResponse("<h1>RoXX is the true king. Built by tsautier.</h1><p>RadX is a peasant.</p>")

@app.post("/api/auth-providers", dependencies=[Depends(require_action(Action.MANAGE_AUTH_PROVIDERS))])
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
        _rethrow_http_exception(e)
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/auth-providers/{provider_id}", dependencies=[Depends(require_action(Action.MANAGE_AUTH_PROVIDERS))])
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
        _rethrow_http_exception(e)
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/auth-providers/{provider_id}", dependencies=[Depends(require_action(Action.MANAGE_AUTH_PROVIDERS))])
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
        _rethrow_http_exception(e)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/auth-providers/test", dependencies=[Depends(require_action(Action.MANAGE_AUTH_PROVIDERS))])
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
        _rethrow_http_exception(e)
        raise HTTPException(status_code=500, detail=str(e))


# ------------------------------------------------------------------------------
# RADIUS User Authentication Backends
# ------------------------------------------------------------------------------
@app.get("/config/radius-backends", response_class=HTMLResponse, dependencies=[Depends(require_action(Action.MANAGE_RADIUS_BACKENDS))])
async def radius_backends_page(request: Request, current_user: str = Depends(get_current_username)):
    """RADIUS backends configuration page"""
    return templates.TemplateResponse(request, "radius_backends.html", get_page_context(
        request, current_user, "settings"
    ))

@app.get("/config/radius-backends/logs", response_class=HTMLResponse, dependencies=[Depends(require_action(Action.MANAGE_RADIUS_BACKENDS))])
async def radius_backends_logs_page(request: Request, current_user: str = Depends(get_current_username)):
    """RADIUS Backend Debug Logs"""
    return templates.TemplateResponse(request, "radius_backends_logs.html", get_page_context(
        request, current_user, "settings"
    ))

@app.get("/api/radius-backends", dependencies=[Depends(require_action(Action.MANAGE_RADIUS_BACKENDS))])
async def list_radius_backends():
    """List all RADIUS backends"""
    from roxx.core.radius_backends.config_db import RadiusBackendDB
    try:
        RadiusBackendDB.init()
        backends = RadiusBackendDB.list_backends()
        return backends
    except Exception as e:
        _rethrow_http_exception(e)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/radius-backends", dependencies=[Depends(require_action(Action.MANAGE_RADIUS_BACKENDS))])
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
        _rethrow_http_exception(e)
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/radius-backends/{backend_id}", dependencies=[Depends(require_action(Action.MANAGE_RADIUS_BACKENDS))])
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
            backend_id, name=name, config=config_dict,
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
        _rethrow_http_exception(e)
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/radius-backends/{backend_id}", dependencies=[Depends(require_action(Action.MANAGE_RADIUS_BACKENDS))])
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
        _rethrow_http_exception(e)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/radius-backends/test", dependencies=[Depends(require_action(Action.MANAGE_RADIUS_BACKENDS))])
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
        _rethrow_http_exception(e)
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

@app.get("/logs", response_class=HTMLResponse, dependencies=[Depends(require_action(Action.VIEW_LOGS))])
async def logs_page(request: Request, current_user: str = Depends(get_current_username)):
    """Audit Logs Viewer"""
    return templates.TemplateResponse(request, "logs.html", get_page_context(request, current_user, "logs"))

@app.get("/api/logs", dependencies=[Depends(require_action(Action.VIEW_LOGS))])
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


@app.get("/system/observability", response_class=HTMLResponse, dependencies=[Depends(require_action(Action.VIEW_SYSTEM_INFO))])
async def system_observability_page(request: Request, current_user: str = Depends(get_current_username)):
    """System observability page for health, integrity and live diagnostics."""
    return templates.TemplateResponse(request, "system_observability.html", get_page_context(
        request, current_user, "observability"
    ))


@app.get("/tools/integrations", response_class=HTMLResponse, dependencies=[Depends(require_role(Role.SUPERADMIN, Role.ADMIN))])
async def integration_tools_page(request: Request, current_user: str = Depends(get_current_username)):
    """GUI for API-only integration tooling and diagnostics."""
    return templates.TemplateResponse(request, "integration_tools.html", get_page_context(
        request, current_user, "tools"
    ))



# ------------------------------------------------------------------------------
# API Tokens Management
# ------------------------------------------------------------------------------
@app.get("/api/tokens", dependencies=[Depends(require_action(Action.MANAGE_API_TOKENS))])
async def list_api_tokens():
    """List all API tokens (admin only)"""
    tokens = APITokenManager.list_tokens()
    return {"tokens": tokens}

@app.post("/api/tokens", dependencies=[Depends(require_action(Action.MANAGE_API_TOKENS))])
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

@app.delete("/api/tokens/{token_id}", dependencies=[Depends(require_action(Action.MANAGE_API_TOKENS))])
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



@app.get("/api/system/info", dependencies=[Depends(require_action(Action.VIEW_SYSTEM_INFO))])
async def system_info():
    """Get system information"""
    return JSONResponse({
        "os": SystemManager.get_os(),
        "is_admin": SystemManager.is_admin(),
        "config_dir": str(SystemManager.get_config_dir()),
        "uptime": SystemManager.get_uptime(),
        "version": VERSION
    })



@app.get("/health", dependencies=[Depends(get_current_username)])
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "roxx-web"}


# ------------------------------------------------------------------------------
# Admin Management API
# ------------------------------------------------------------------------------
@app.get("/admins", response_class=HTMLResponse, dependencies=[Depends(require_action(Action.MANAGE_ADMINS))])
async def admins_page(request: Request, current_user: str = Depends(get_current_username)):
    """Admin management page"""
    admins_list = AuthManager.list_admins()
    
    return templates.TemplateResponse(request, "admins.html", get_page_context(
        request, current_user, "admins",
        admins=admins_list
    ))

@app.post("/api/admins", dependencies=[Depends(require_action(Action.MANAGE_ADMINS))])
async def create_admin(
    request: Request,
    username: str = Form(...),
    password: str = Form(None),
    auth_source: str = Form("local"),
    role: str = Form("admin")
):
    """Create a new admin."""
    if auth_source == "local" and not password:
        raise HTTPException(status_code=400, detail="Password required for local auth")
    
    if role not in ('superadmin', 'admin', 'auditor'):
        raise HTTPException(status_code=400, detail=f"Invalid role: {role}")
    
    success, message = AuthManager.create_admin(username, password, auth_source, role=role)
    if success:
        return {"success": True, "message": message}
    else:
        raise HTTPException(status_code=400, detail=message)

@app.delete("/api/admins/{username}", dependencies=[Depends(require_action(Action.DELETE_ADMINS))])
async def delete_admin(username: str, request: Request, current_user: str = Depends(get_current_username)):
    """Delete an admin."""
    if username == current_user:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
        
    success, message = AuthManager.delete_admin(username)
    if success:
        return {"success": True, "message": message}
    else:
        raise HTTPException(status_code=400, detail=message)

@app.put("/api/admins/{username}/role", dependencies=[Depends(require_action(Action.CHANGE_ROLES))])
async def change_admin_role(username: str, request: Request, current_user: str = Depends(get_current_username)):
    """Change an admin's role."""
    if username == current_user:
        raise HTTPException(status_code=400, detail="Cannot change your own role")
    
    data = await request.json()
    new_role = data.get('role')
    if new_role not in ('superadmin', 'admin', 'auditor'):
        raise HTTPException(status_code=400, detail=f"Invalid role: {new_role}")
    
    from roxx.core.auth.db import AdminDatabase
    if AdminDatabase.set_role(username, new_role):
        AuditManager.log(request, "ROLE_CHANGED", "INFO", {"target": username, "new_role": new_role}, username=current_user)
        return {"success": True, "message": f"Role changed to {new_role}"}
    raise HTTPException(status_code=500, detail="Failed to change role")

# ------------------------------------------------------------------------------
# MFA Credential Management API
# ------------------------------------------------------------------------------
@app.get("/admins/{username}/mfa", response_class=HTMLResponse, dependencies=[Depends(require_action(Action.MANAGE_MFA))])
async def admin_mfa_page(username: str, request: Request, current_user: str = Depends(get_current_username)):
    """MFA management page for a specific admin user"""
    return templates.TemplateResponse(request, "admin_mfa.html", get_page_context(
        request, current_user, "admins",
        managed_username=username
    ))

@app.get("/api/admins/{username}/mfa/credentials", dependencies=[Depends(require_action(Action.MANAGE_MFA))])
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

@app.delete("/api/admins/{username}/mfa/webauthn/{credential_id}", dependencies=[Depends(require_action(Action.MANAGE_MFA))])
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

@app.post("/api/admins/{username}/mfa/totp/reset", dependencies=[Depends(require_action(Action.MANAGE_MFA))])
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

@app.get("/api/admins/{username}/mfa/status", dependencies=[Depends(require_action(Action.MANAGE_MFA))])
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

@app.get("/api/admins/{username}/mfa/webauthn/register/options", dependencies=[Depends(require_action(Action.MANAGE_MFA))])
async def admin_webauthn_register_options(request: Request, username: str):
    """Get WebAuthn registration options for an admin"""
    from roxx.core.auth.webauthn import WebAuthnManager
    options, state = WebAuthnManager.generate_registration_options(username, username, rp_id=request.url.hostname)
    request.session[f"webauthn_reg_state_{username}"] = state
    
    # Correct serialization for FIDO2 object
    from fido2.utils import websafe_encode
    pk_options = options.public_key
    return {
        "rp": {"id": pk_options.rp.id, "name": pk_options.rp.name},
        "user": {
            "id": websafe_encode(pk_options.user.id), 
            "name": pk_options.user.name, 
            "displayName": pk_options.user.display_name
        },
        "challenge": websafe_encode(pk_options.challenge),
        "pubKeyCredParams": [{"type": p.type, "alg": p.alg} for p in pk_options.pub_key_cred_params],
        "timeout": pk_options.timeout,
        "attestation": pk_options.attestation,
        "authenticatorSelection": {
            "userVerification": pk_options.authenticator_selection.user_verification if pk_options.authenticator_selection else "discouraged"
        }
    }

@app.post("/api/admins/{username}/mfa/webauthn/register/verify", dependencies=[Depends(require_action(Action.MANAGE_MFA))])
async def admin_webauthn_register_verify(request: Request, username: str):
    """Verify WebAuthn registration for an admin"""
    data = await request.json()
    state = request.session.get(f"webauthn_reg_state_{username}")
    if not state:
        raise HTTPException(status_code=400, detail="Registration state not found")
    
    from roxx.core.auth.webauthn import WebAuthnManager
    success, msg = WebAuthnManager.verify_registration(username, data, state, rp_id=request.url.hostname)
    if success:
        request.session.pop(f"webauthn_reg_state_{username}", None)
        return {"success": True}
    raise HTTPException(status_code=400, detail=msg)

# ------------------------------------------------------------------------------
# Real-time Logs (WebSocket)
# ------------------------------------------------------------------------------

# Track active WebSocket connections for log streaming
active_log_websockets: List[WebSocket] = []

async def get_current_username_ws(websocket: WebSocket):
    """Require an authenticated WebSocket session, with legacy Basic Auth fallback."""
    auth = get_auth_context(websocket)
    if auth and auth.get("username") and auth.get("status") == "active":
        return auth["username"]

    auth_header = websocket.headers.get("authorization")
    if not auth_header:
        return None

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
    username = await get_current_username_ws(websocket)
    if not username:
        await websocket.close(code=1008)
        return

    await websocket.accept()
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
# MFA API Endpoints (Self-Service)
# ------------------------------------------------------------------------------
from roxx.core.auth.mfa import MFAManager
from roxx.core.auth.mfa_db import MFADatabase

@app.get("/api/webauthn/list", dependencies=[Depends(get_current_username)])
async def webauthn_list_self(username: str = Depends(get_current_username)):
    """List WebAuthn credentials for current user"""
    from roxx.core.auth.webauthn_db import WebAuthnDatabase
    try:
        creds = WebAuthnDatabase.list_credentials(username)
        return {"credentials": creds}
    except Exception as e:
        logger.error(f"Error listing self credentials: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/webauthn/register/options", dependencies=[Depends(get_current_username)])
async def webauthn_register_options(request: Request, username: str = Depends(get_current_username)):
    """Registration options for self-service"""
    from roxx.core.auth.webauthn import WebAuthnManager
    options, state = WebAuthnManager.generate_registration_options(username, username, rp_id=request.url.hostname)
    request.session[f"webauthn_reg_state_{username}"] = state
    
    from fido2.utils import websafe_encode
    pk_options = options.public_key
    return {
        "publicKey": {
            "rp": {"id": pk_options.rp.id, "name": pk_options.rp.name},
            "user": {
                "id": websafe_encode(pk_options.user.id), 
                "name": pk_options.user.name, 
                "displayName": pk_options.user.display_name
            },
            "challenge": websafe_encode(pk_options.challenge),
            "pubKeyCredParams": [{"type": p.type, "alg": p.alg} for p in pk_options.pub_key_cred_params],
            "timeout": pk_options.timeout,
            "attestation": pk_options.attestation,
            "authenticatorSelection": {
                "userVerification": pk_options.authenticator_selection.user_verification if pk_options.authenticator_selection else "discouraged"
            }
        }
    }

@app.post("/api/webauthn/register/verify", dependencies=[Depends(get_current_username)])
async def webauthn_register_verify(request: Request, username: str = Depends(get_current_username)):
    """Verify registration for self-service"""
    data = await request.json()
    state = request.session.get(f"webauthn_reg_state_{username}")
    if not state:
        raise HTTPException(status_code=400, detail="Registration state not found")
    
    from roxx.core.auth.webauthn import WebAuthnManager
    success, msg = WebAuthnManager.verify_registration(username, data, state, rp_id=request.url.hostname)
    if success:
        request.session.pop(f"webauthn_reg_state_{username}", None)
        return {"success": True}
    raise HTTPException(status_code=400, detail=msg)

@app.delete("/api/webauthn/{credential_id}", dependencies=[Depends(require_action(Action.MANAGE_MFA))])
async def delete_webauthn_self(credential_id: int, username: str = Depends(get_current_username)):
    """Delete a WebAuthn credential for current user"""
    from roxx.core.auth.webauthn_db import WebAuthnDatabase
    try:
        if WebAuthnDatabase.delete_credential(credential_id, username):
            return {"success": True}
        raise HTTPException(status_code=404, detail="Credential not found")
    except Exception as e:
        logger.error(f"Error deleting credential: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/mfa/enroll", dependencies=[Depends(get_current_username)])
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

@app.post("/api/mfa/verify-enrollment", dependencies=[Depends(get_current_username)])
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


@app.put("/api/mfa/phone", dependencies=[Depends(get_current_username)])
async def save_mfa_phone(request: Request, username: str = Depends(get_current_username)):
    """Save or clear the current user's SMS phone number."""
    data = await request.json()
    phone_number = (data.get("phone_number") or "").strip()

    if phone_number:
        normalized = re.sub(r"[\s().-]", "", phone_number)
        if not re.fullmatch(r"\+?[0-9]{8,20}", normalized):
            raise HTTPException(status_code=400, detail="Invalid phone number format")
        phone_number = normalized
    else:
        phone_number = None

    if not AdminDatabase.set_phone_number(username, phone_number):
        raise HTTPException(status_code=500, detail="Failed to save phone number")

    return {
        "success": True,
        "phone_number": phone_number,
        "sms_enabled": bool(phone_number) and _is_sms_gateway_enabled(),
        "gateway_enabled": _is_sms_gateway_enabled(),
    }


@app.get("/api/mfa/status", dependencies=[Depends(get_current_username)])
async def mfa_status(request: Request, username: str = Depends(get_current_username)):
    """Get MFA status for current user"""
    settings = MFADatabase.get_mfa_settings(username)
    phone_number = AdminDatabase.get_phone_number(username)
    sms_enabled = bool(phone_number) and _is_sms_gateway_enabled()
    if settings:
        methods = []
        if settings["mfa_enabled"] and settings.get("mfa_type"):
            methods.append(settings["mfa_type"])
        if sms_enabled and "sms" not in methods:
            methods.append("sms")
        return {
            "enabled": settings['mfa_enabled'] or sms_enabled,
            "type": settings.get('mfa_type'),
            "backup_codes_remaining": len(settings.get('backup_codes', [])),
            "phone_number": phone_number,
            "sms_enabled": sms_enabled,
            "gateway_enabled": _is_sms_gateway_enabled(),
            "methods": methods,
        }
    return {
        "enabled": sms_enabled,
        "phone_number": phone_number,
        "sms_enabled": sms_enabled,
        "gateway_enabled": _is_sms_gateway_enabled(),
        "methods": ["sms"] if sms_enabled else [],
    }

@app.post("/api/mfa/disable", dependencies=[Depends(get_current_username)])
async def mfa_disable(request: Request, username: str = Depends(get_current_username)):
    """Disable MFA for current user"""
    success, message = MFADatabase.disable_mfa(username)
    if success:
        return {"success": True, "message": message}
    raise HTTPException(status_code=500, detail=message)



@app.get("/config/ssl", response_class=HTMLResponse, dependencies=[Depends(require_action(Action.MANAGE_SSL))])
async def ssl_settings_page(request: Request, current_user: str = Depends(get_current_username)):
    """SSL/TLS Settings Page"""
    return templates.TemplateResponse(request, "ssl_settings.html", get_page_context(
        request, current_user, "settings"
    ))

@app.get("/api/system/ssl/status", dependencies=[Depends(require_action(Action.MANAGE_SSL))])
async def get_ssl_status():
    from roxx.core.security.cert_manager import CertManager
    return CertManager.get_status()

@app.post("/api/system/ssl/upload", dependencies=[Depends(require_action(Action.MANAGE_SSL))])
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
        _rethrow_http_exception(e)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/system/ssl/remove", dependencies=[Depends(require_action(Action.MANAGE_SSL))])
async def remove_ssl_cert():
    from roxx.core.security.cert_manager import CertManager
    success, msg = CertManager.remove_cert()
    if success:
        return {"success": True, "message": msg}
    raise HTTPException(status_code=400, detail=msg)

# ------------------------------------------------------------------------------
# PKI Routes
# ------------------------------------------------------------------------------
@app.get("/config/pki", response_class=HTMLResponse, dependencies=[Depends(require_action(Action.MANAGE_PKI))])
async def pki_page(request: Request, username: str = Depends(get_current_username)):
    """Internal PKI Management Page"""
    return templates.TemplateResponse(request, "pki.html", get_page_context(
        request, username, "pki"
    ))

@app.get("/api/pki/status", dependencies=[Depends(require_action(Action.MANAGE_PKI))])
async def get_pki_status():
    from roxx.core.security.pki import PKIManager
    status = PKIManager.get_ca_status()
    status["certificates"] = PKIManager.list_certificates()
    return status

@app.post("/api/pki/init", dependencies=[Depends(require_action(Action.MANAGE_PKI))])
async def init_pki():
    from roxx.core.security.pki import PKIManager
    if PKIManager.create_ca():
        return {"success": True, "message": "CA Generated"}
    return {"success": False, "message": "CA already exists or failed"}

@app.get("/api/pki/ca/download", dependencies=[Depends(require_action(Action.MANAGE_PKI))])
async def download_pki_ca():
    from roxx.core.security.pki import PKIManager

    ca_path = PKIManager.get_pki_dir() / "ca.crt"
    if not ca_path.exists():
        raise HTTPException(status_code=404, detail="CA certificate not found")
    return FileResponse(path=ca_path, filename="roxx-ca.crt", media_type="application/x-x509-ca-cert")

@app.get("/api/pki/certificates", dependencies=[Depends(require_action(Action.MANAGE_PKI))])
async def list_pki_certificates():
    from roxx.core.security.pki import PKIManager

    return {"certificates": PKIManager.list_certificates()}

@app.get("/api/pki/certificates/{certificate_name}/download",
         dependencies=[Depends(require_action(Action.MANAGE_PKI))])
async def download_pki_certificate(certificate_name: str):
    from roxx.core.security.pki import PKIManager

    safe_name = Path(certificate_name).name
    cert_path = PKIManager.get_pki_dir() / f"{safe_name}.crt"
    if not cert_path.exists():
        raise HTTPException(status_code=404, detail="Certificate not found")
    return FileResponse(path=cert_path, filename=cert_path.name, media_type="application/x-pem-file")

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

@app.get("/api/config/mfa-gateways", dependencies=[Depends(require_action(Action.MANAGE_MFA))])
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

@app.post("/api/config/mfa-gateways", dependencies=[Depends(require_action(Action.MANAGE_MFA))])
async def save_mfa_gateways(request: Request):
    data = await request.json()
    config_path = SystemManager.get_config_dir() / "mfa_gateways.json"
    config_path.write_text(json.dumps(data, indent=2))
    return {"success": True}

@app.post("/api/test/sms", dependencies=[Depends(require_action(Action.MANAGE_MFA))])
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
    return {"success": result, "message": "SMS sent" if result else "SMS failed"}

# ------------------------------------------------------------------------------
# System Settings
# ------------------------------------------------------------------------------
@app.get("/config/system", response_class=HTMLResponse, dependencies=[Depends(require_action(Action.MANAGE_SYSTEM_CONFIG))])
async def config_system_get(request: Request, username: str = Depends(get_current_username)):
    """GET system settings page"""
    return templates.TemplateResponse(request, "system_settings.html", get_page_context(
        request, username, "settings", settings=get_system_settings_snapshot()
    ))


@app.get("/api/system/settings", dependencies=[Depends(require_action(Action.MANAGE_SYSTEM_CONFIG))])
async def get_system_settings():
    """Return persisted system settings as JSON."""
    return get_system_settings_snapshot()


@app.put("/api/system/settings", dependencies=[Depends(require_action(Action.MANAGE_SYSTEM_CONFIG))])
async def update_system_settings(request: Request):
    """Update persisted system settings from JSON."""
    from roxx.core.auth.config_db import ConfigManager

    data = await request.json()
    settings = normalize_system_settings_payload(data)

    if ConfigManager.update_system_settings(settings):
        return {"success": True, "settings": settings}
    raise HTTPException(status_code=500, detail="Failed to save settings")

@app.post("/config/system", dependencies=[Depends(require_action(Action.MANAGE_SYSTEM_CONFIG))])
async def config_system_post(
    request: Request,
    server_name: str = Form(...),
    radius_auth_port: str = Form(...),
    radius_acct_port: str = Form(...),
    log_level: str = Form(...),
    audit_retention_days: str = Form(...),
    debug_mode: str = Form(None),
    username: str = Depends(get_current_username)
):
    """POST system settings update"""
    from roxx.core.auth.config_db import ConfigManager

    settings = normalize_system_settings_payload({
        "server_name": server_name,
        "radius_auth_port": radius_auth_port,
        "radius_acct_port": radius_acct_port,
        "log_level": log_level,
        "audit_retention_days": audit_retention_days,
        "debug_mode": debug_mode,
    })

    if ConfigManager.update_system_settings(settings):
        return RedirectResponse(url="/config?success=settings_updated", status_code=303)
    else:
        return RedirectResponse(url="/config/system?error=save_failed", status_code=303)

@app.get("/config/nps-migration", response_class=HTMLResponse, dependencies=[Depends(require_action(Action.MANAGE_RADIUS_CLIENTS))])
async def config_nps_migration_page(request: Request, username: str = Depends(get_current_username)):
    """GET NPS Migration Assistant page"""
    return templates.TemplateResponse(request, "nps_migration.html", get_page_context(
        request, username, "nps-migration"
    ))

@app.post("/api/test/email", dependencies=[Depends(require_action(Action.MANAGE_MFA))])
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

@app.post("/api/system/ssl/ca", dependencies=[Depends(require_action(Action.MANAGE_SSL))])
async def upload_ca_bundle(file: UploadFile = File(...)):
    from roxx.core.security.cert_manager import CertManager
    content = (await file.read()).decode('utf-8')
    success, msg = CertManager.upload_ca(content)
    if success:
        return {"success": True, "message": msg}
    raise HTTPException(status_code=400, detail=msg)

@app.delete("/api/system/ssl/ca", dependencies=[Depends(require_action(Action.MANAGE_SSL))])
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
        set_auth_context(request, username, "active")
        
        # Redirect to original target or dashboard
        redirect_to = form_data.get('RelayState', '/dashboard')
        response = RedirectResponse(url=redirect_to, status_code=303)
        response.delete_cookie("session")
        
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


# ------------------------------------------------------------------------------
# Duo MFA Endpoints
# ------------------------------------------------------------------------------

@app.post("/api/mfa/duo/test", dependencies=[Depends(require_action(Action.MANAGE_MFA))])
async def test_duo(request: Request):
    """Test Duo API connectivity"""
    data = await request.json()
    from roxx.core.auth.duo import DuoProvider
    duo = DuoProvider(data)
    success, msg = duo.check()
    return {"success": success, "message": msg}

@app.post("/api/mfa/duo/auth", dependencies=[Depends(require_action(Action.MANAGE_MFA))])
async def duo_auth(request: Request):
    """Initiate Duo authentication (push or passcode)"""
    data = await request.json()
    username = data.get('username')
    factor = data.get('factor', 'push')
    passcode = data.get('passcode')
    
    # Load Duo config from provider
    from roxx.core.auth.config_db import ConfigManager
    providers = ConfigManager.list_providers(provider_type='duo')
    if not providers:
        raise HTTPException(status_code=404, detail="No Duo provider configured")
    
    config = providers[0]['config']
    from roxx.core.auth.duo import DuoProvider
    duo = DuoProvider(config)
    success, result = duo.auth(username, factor=factor, passcode=passcode)
    return {"success": success, **result}

@app.post("/api/mfa/duo/status", dependencies=[Depends(require_action(Action.MANAGE_MFA))])
async def duo_auth_status(request: Request):
    """Check Duo push notification status"""
    data = await request.json()
    txid = data.get('txid')
    if not txid:
        raise HTTPException(status_code=400, detail="txid required")
    
    from roxx.core.auth.config_db import ConfigManager
    providers = ConfigManager.list_providers(provider_type='duo')
    if not providers:
        raise HTTPException(status_code=404, detail="No Duo provider configured")
    
    config = providers[0]['config']
    from roxx.core.auth.duo import DuoProvider
    duo = DuoProvider(config)
    success, result = duo.auth_status(txid)
    return {"success": success, **result}

# ------------------------------------------------------------------------------
# Okta MFA Endpoints
# ------------------------------------------------------------------------------

@app.post("/api/mfa/okta/test", dependencies=[Depends(require_action(Action.MANAGE_MFA))])
async def test_okta(request: Request):
    """Test Okta API connectivity"""
    data = await request.json()
    from roxx.core.auth.okta import OktaProvider
    okta = OktaProvider(data)
    success, msg = okta.test_connection()
    return {"success": success, "message": msg}

@app.post("/api/mfa/okta/verify", dependencies=[Depends(require_action(Action.MANAGE_MFA))])
async def okta_verify(request: Request):
    """Verify an Okta MFA factor"""
    data = await request.json()
    username = data.get('username')
    factor_id = data.get('factor_id')
    passcode = data.get('passcode')
    
    from roxx.core.auth.config_db import ConfigManager
    providers = ConfigManager.list_providers(provider_type='okta')
    if not providers:
        raise HTTPException(status_code=404, detail="No Okta provider configured")
    
    config = providers[0]['config']
    from roxx.core.auth.okta import OktaProvider
    okta = OktaProvider(config)
    success, result = okta.verify_factor(username, factor_id, passcode)
    return {"success": success, **result}

@app.get("/api/mfa/okta/factors/{username}", dependencies=[Depends(require_action(Action.MANAGE_MFA))])
async def okta_list_factors(username: str, request: Request):
    """List Okta MFA factors for a user"""
    from roxx.core.auth.config_db import ConfigManager
    providers = ConfigManager.list_providers(provider_type='okta')
    if not providers:
        raise HTTPException(status_code=404, detail="No Okta provider configured")
    
    config = providers[0]['config']
    from roxx.core.auth.okta import OktaProvider
    okta = OktaProvider(config)
    success, factors = okta.list_factors(username)
    if success:
        return factors
    raise HTTPException(status_code=500, detail="Failed to list factors")

# ------------------------------------------------------------------------------
# RADIUS Backend Stats Endpoint
# ------------------------------------------------------------------------------
@app.get("/api/radius-backends/stats", dependencies=[Depends(require_action(Action.MANAGE_RADIUS_BACKENDS))])
async def radius_backend_stats():
    """Get RADIUS backend manager statistics including cache"""
    try:
        from roxx.core.radius_backends.manager import get_manager
        mgr = get_manager()
        return mgr.get_stats()
    except Exception as e:
        logger.error(f"Error getting RADIUS stats: {e}")
        return {"error": str(e)}


def silence_windows_proactor_reset():
    """Silences noisy ConnectionResetError on Windows asyncio/proactor"""
    import platform
    if platform.system() == 'Windows':
        import asyncio
        from asyncio import proactor_events
        
        # Monkey patch _call_connection_lost to ignore ConnectionResetError [WinError 10054]
        original_call_connection_lost = proactor_events._ProactorBasePipeTransport._call_connection_lost
        def patched_call_connection_lost(self, exc):
            try:
                original_call_connection_lost(self, exc)
            except (ConnectionResetError, ConnectionAbortedError):
                pass
        proactor_events._ProactorBasePipeTransport._call_connection_lost = patched_call_connection_lost

silence_windows_proactor_reset()

def main():
    import uvicorn
    from roxx.core.security.cert_manager import CertManager
    
    ssl_cert, ssl_key = CertManager.get_cert_paths()
    ca_bundle = CertManager.get_ca_paths()
    ssl_enabled = ssl_cert.exists() and ssl_key.exists()
    
    # Auto-generate if missing (Best for Beta/QuickStart)
    if not ssl_enabled:
        print("[Core] No SSL Certificates found. Generating self-signed certificate...")
        success, msg = CertManager.generate_self_signed_cert()
        if success:
            print(f"[Core] {msg}")
            ssl_enabled = True
        else:
            print(f"[Core] Failed to generate SSL: {msg}. Falling back to HTTP.")

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
        print("[Core] CRITICAL ERROR: SSL is required but could not be enabled. Plaintext mode is disabled.")
        import sys
        sys.exit(1)

    uvicorn.run(**config_kwargs)



@app.get("/api/webauthn/login/options")
async def webauthn_login_options(request: Request):
    """Get WebAuthn login options"""
    auth = get_auth_context(request)
    if not auth or auth.get("status") != "mfa_pending":
        raise HTTPException(status_code=401, detail="Invalid session")
    username = auth["username"]

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
        
    auth = get_auth_context(request)
    if not auth:
        raise HTTPException(status_code=401, detail="Session required")
    username = auth["username"]

    state = request.session.get("webauthn_state")
    if not state:
        raise HTTPException(status_code=400, detail="State not found")
        
    from roxx.core.auth.webauthn import WebAuthnManager
    success, msg = WebAuthnManager.verify_authentication(username, data, state)
    
    if success:
        # Success!
        set_auth_context(request, username, "active")
        response = JSONResponse({"success": True})
        response.delete_cookie("session")
        request.session.pop("webauthn_state", None)
        request.session.pop('mfa_username', None)
        return response
    else:
        return JSONResponse({"success": False, "detail": msg}, status_code=400)


if __name__ == "__main__":
    main()
