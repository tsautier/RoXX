# Add these MFA endpoints before the final "if __name__ == '__main__':" section

# ------------------------------------------------------------------------------
# MFA API Endpoints
# ------------------------------------------------------------------------------
from roxx.core.auth.mfa import MFAManager
from roxx.core.auth.mfa_db import MFADatabase

@app.post("/api/mfa/enroll", dependencies=[Depends(get_current_username)])
async def mfa_enroll(request: Request):
    """
    Start MFA enrollment for current user
    Returns TOTP secret and QR code
    """
    username = request.session.get("username")
    
    # Generate secret and QR code
    secret = MFAManager.generate_secret()
    totp_uri = MFAManager.generate_totp_uri(username, secret)
    qr_code_data = MFAManager.generate_qr_code(totp_uri)
    
    # Generate backup codes
    plain_codes, hashed_codes = MFAManager.generate_backup_codes(10)
    
    # Store in session temporarily (not in DB until verified)
    request.session['mfa_enrollment'] = {
        'secret': secret,
        'backup_codes': hashed_codes
    }
    
    return {
        "success": True,
        "secret": secret,
        "qr_code": qr_code_data,
        "backup_codes": plain_codes,
        "message": "Scan QR code with authenticator app and verify"
    }


@app.post("/api/mfa/verify-enrollment", dependencies=[Depends(get_current_username)])
async def mfa_verify_enrollment(
    request: Request,
    token: str = Form(...)
):
    """
    Verify TOTP token and complete enrollment
    """
    username = request.session.get("username")
    enrollment = request.session.get('mfa_enrollment')
    
    if not enrollment:
        raise HTTPException(status_code=400, detail="No enrollment in progress")
    
    secret = enrollment['secret']
    backup_codes = enrollment['backup_codes']
    
    # Verify token
    if not MFAManager.verify_totp(secret, token):
        raise HTTPException(status_code=400, detail="Invalid token")
    
    # Save to database
    success, message = MFADatabase.enroll_totp(username, secret, backup_codes)
    
    if success:
        # Clear session enrollment data
        request.session.pop('mfa_enrollment', None)
        return {"success": True, "message": "MFA enabled successfully"}
    else:
        raise HTTPException(status_code=500, detail=message)


@app.post("/api/mfa/verify", dependencies=[Depends(get_current_username)])
async def mfa_verify(
    request: Request,
    token: str = Form(...)
):
    """
    Verify TOTP token for already enrolled user
    """
    username = request.session.get("username")
    
    settings = MFADatabase.get_mfa_settings(username)
    if not settings or not settings.get('mfa_enabled'):
        raise HTTPException(status_code=400, detail="MFA not enabled")
    
    secret = settings['totp_secret']
    
    # Try TOTP first
    if MFAManager.verify_totp(secret, token):
        MFADatabase.update_last_used(username)
        return {"success": True, "message": "Token verified"}
    
    # Try backup code
    success, message = MFADatabase.verify_and_consume_backup_code(username, token)
    if success:
        return {"success": True, "message": message}
    
    raise HTTPException(status_code=400, detail="Invalid token or backup code")


@app.post("/api/mfa/disable", dependencies=[Depends(get_current_username)])
async def mfa_disable(request: Request):
    """Disable MFA for current user"""
    username = request.session.get("username")
    
    success, message = MFADatabase.disable_mfa(username)
    
    if success:
        return {"success": True, "message": message}
    else:
        raise HTTPException(status_code=500, detail=message)


@app.get("/api/mfa/status", dependencies=[Depends(get_current_username)])
async def mfa_status(request: Request):
    """Get MFA status for current user"""
    username = request.session.get("username")
    
    settings = MFADatabase.get_mfa_settings(username)
    
    if settings:
        backup_count = len(settings.get('backup_codes', []))
        return {
            "enabled": settings['mfa_enabled'],
            "type": settings.get('mfa_type'),
            "backup_codes_remaining": backup_count,
            "last_used": settings.get('last_used')
        }
    else:
        return {
            "enabled": False,
            "type": None,
            "backup_codes_remaining": 0,
            "last_used": None
        }


@app.post("/api/mfa/regenerate-backup-codes", dependencies=[Depends(get_current_username)])
async def mfa_regenerate_backup_codes(request: Request):
    """Regenerate backup codes for user"""
    username = request.session.get("username")
    
    settings = MFADatabase.get_mfa_settings(username)
    if not settings or not settings.get('mfa_enabled'):
        raise HTTPException(status_code=400, detail="MFA not enabled")
    
    # Generate new codes
    plain_codes, hashed_codes = MFAManager.generate_backup_codes(10)
    
    # Update in database
    import json
    cursor = db_conn.cursor()
    cursor.execute('''
        UPDATE user_mfa 
        SET backup_codes = ?
        WHERE username = ?
    ''', (json.dumps(hashed_codes), username))
    db_conn.commit()
    
    return {
        "success": True,
        "backup_codes": plain_codes,
        "message": "New backup codes generated"
    }
