"""
RoXX Web Interface - Modern FastAPI Application
Replaces the old SimpleSAMLphp interface with a modern Python web app
"""

from fastapi import FastAPI, Request, Form, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import qrcode
import io
import base64
import os
import secrets
import asyncio
from pathlib import Path
from typing import List

from roxx.core.auth.totp import TOTPAuthenticator
from roxx.utils.system import SystemManager

# ------------------------------------------------------------------------------
# Security & Authentication
# ------------------------------------------------------------------------------
security = HTTPBasic()

def get_current_username(credentials: HTTPBasicCredentials = Depends(security)):
    """Verifies HTTP Basic Auth credentials"""
    correct_username = os.getenv("ROXX_ADMIN_USER", "admin").encode("utf8")
    correct_password = os.getenv("ROXX_ADMIN_PASSWORD", "admin").encode("utf8")
    
    is_correct_username = secrets.compare_digest(credentials.username.encode("utf8"), correct_username)
    is_correct_password = secrets.compare_digest(credentials.password.encode("utf8"), correct_password)
    
    if not (is_correct_username and is_correct_password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

# ------------------------------------------------------------------------------
# App Initialization
# ------------------------------------------------------------------------------

app = FastAPI(
    title="RoXX Admin Interface",
    description="Modern web interface for RoXX RADIUS Authentication Proxy",
    version="1.0.0-beta2",
    dependencies=[Depends(get_current_username)] # Secure ALL endpoints
)

# Templates directory
templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

# Static files
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page"""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "title": "RoXX Admin"
    })


@app.get("/totp/enroll", response_class=HTMLResponse)
async def totp_enroll_page(request: Request):
    """TOTP enrollment page"""
    return templates.TemplateResponse("totp_enroll.html", {
        "request": request,
        "title": "TOTP Enrollment"
    })


@app.post("/api/totp/generate-qr")
async def generate_totp_qr(
    username: str = Form(...),
    issuer: str = Form(default="RoXX")
):
    """Generate TOTP QR code"""
    try:
        # Generate a random secret
        import secrets
        secret = base64.b32encode(secrets.token_bytes(20)).decode('utf-8')
        
        # Create TOTP URI
        totp_uri = f"otpauth://totp/{issuer}:{username}?secret={secret}&issuer={issuer}&algorithm=SHA1&digits=6&period=30"
        
        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        return JSONResponse({
            "success": True,
            "qr_code": f"data:image/png;base64,{img_str}",
            "secret": secret,
            "uri": totp_uri
        })
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/totp/verify")
async def verify_totp(
    secret: str = Form(...),
    code: str = Form(...)
):
    """Verify TOTP code"""
    try:
        totp = TOTPAuthenticator(secret=secret)
        is_valid = totp.verify(code)
        
        return JSONResponse({
            "success": True,
            "valid": is_valid
        })
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))





@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Dashboard page"""
    from roxx.core.services import ServiceManager as SvcMgr
    
    # Check FreeRADIUS status (process name usually 'freeradius' or 'radiusd')
    radius_active = SystemManager.is_service_running('freeradius') or SystemManager.is_service_running('radiusd')
    radius_status = "UP" if radius_active else "DOWN"
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "os_type": SystemManager.get_os(),
        "radius_status": radius_status,
        "uptime": SystemManager.get_uptime()
    })


@app.get("/users", response_class=HTMLResponse)
async def users_page(request: Request):
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
        
    return templates.TemplateResponse("users.html", {
        "request": request,
        "users": users_list or ["admin (demo)"]
    })


@app.get("/config", response_class=HTMLResponse)
async def config_page(request: Request):
    """Configuration page"""
    return templates.TemplateResponse("config.html", {
        "request": request
    })


@app.get("/api/system/info")
async def system_info():
    """Get system information"""
    return JSONResponse({
        "os": SystemManager.get_os(),
        "is_admin": SystemManager.is_admin(),
        "config_dir": str(SystemManager.get_config_dir()),
        "uptime": SystemManager.get_uptime(),
        "version": "1.0.0-beta2"
    })


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "roxx-web"}


def main():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
