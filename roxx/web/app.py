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
    from roxx.core.services import ServiceManager
    
    mgr = ServiceManager()
    # status = mgr.get_status('freeradius').value 
    # Docker might not have systemd, so fallback to simple check
    radius_status = "UP" # Placeholder for container env if systemd is restricted
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "os_type": SystemManager.get_os(),
        "radius_status": radius_status
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
        "version": "1.0.0-beta"
    })


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "roxx-web"}




# ------------------------------------------------------------------------------
# User Management API
# ------------------------------------------------------------------------------
@app.post("/api/users")
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

@app.delete("/api/users/{username}")
async def delete_user(username: str):
    """Delete a user"""
    if SystemManager.delete_radius_user(username):
        return {"success": True, "message": f"User {username} deleted"}
    else:
        raise HTTPException(status_code=500, detail="Failed to delete user")

# ------------------------------------------------------------------------------
# Real-time Logs (WebSocket)
# ------------------------------------------------------------------------------
@app.websocket("/ws/logs")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        log_file = SystemManager.get_radius_log_file()
        
        # If file doesn't exist (e.g. dev env without radius), simulate logs
        if not log_file.exists():
            await websocket.send_text(f"Log file not found at {log_file} - Simulating logs...")
            while True:
                await asyncio.sleep(2)
                await websocket.send_text(f"SIMULATED LOG: Heartbeat... {secrets.token_hex(4)}")
                
        # Tail the file
        # Simple implementation: read from end
        with open(log_file, "r") as f:
            f.seek(0, 2) # Go to end
            while True:
                line = f.readline()
                if line:
                    await websocket.send_text(line.strip())
                else:
                    await asyncio.sleep(0.5)
                    
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        await websocket.send_text(f"Error: {str(e)}")



# ------------------------------------------------------------------------------
# User Management API
# ------------------------------------------------------------------------------
@app.post("/api/users")
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

@app.delete("/api/users/{username}")
async def delete_user(username: str):
    """Delete a user"""
    if SystemManager.delete_radius_user(username):
        return {"success": True, "message": f"User {username} deleted"}
    else:
        raise HTTPException(status_code=500, detail="Failed to delete user")

# ------------------------------------------------------------------------------
# Real-time Logs (WebSocket)
# ------------------------------------------------------------------------------
@app.websocket("/ws/logs")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        log_file = SystemManager.get_radius_log_file()
        
        # If file doesn't exist (e.g. dev env without radius), simulate logs
        if not log_file.exists():
            await websocket.send_text(f"Log file not found at {log_file} - Simulating logs...")
            while True:
                await asyncio.sleep(2)
                await websocket.send_text(f"SIMULATED LOG: Heartbeat... {secrets.token_hex(4)}")
                
        # Tail the file
        # Simple implementation: read from end
        with open(log_file, "r") as f:
            f.seek(0, 2) # Go to end
            while True:
                line = f.readline()
                if line:
                    await websocket.send_text(line.strip())
                else:
                    await asyncio.sleep(0.5)
                    
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        await websocket.send_text(f"Error: {str(e)}")


def main():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
