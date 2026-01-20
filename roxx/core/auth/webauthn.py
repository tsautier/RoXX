"""
WebAuthn Manager using fido2 library
"""
import logging
import json
import base64
from fido2.webauthn import PublicKeyCredentialRpEntity, PublicKeyCredentialUserEntity, PublicKeyCredentialParameters
from fido2.server import Fido2Server
from fido2.utils import websafe_encode, websafe_decode
from roxx.core.auth.webauthn_db import WebAuthnDatabase

logger = logging.getLogger("roxx.auth.webauthn")

# Configuration (Should be loaded from config)
RP_ID = "localhost" # Domain
RP_NAME = "RoXX Authentication"
ORIGIN = "https://localhost:8000" # Must match exactly, includes protocol and port

class WebAuthnManager:
    server = Fido2Server(
        PublicKeyCredentialRpEntity(id=RP_ID, name=RP_NAME),
        verify_origin=lambda o: True # Allow any origin for dev/beta (or check against ORIGIN)
    )

    @staticmethod
    def init():
        WebAuthnDatabase.init()

    @staticmethod
    def generate_registration_options(username: str, user_id: str):
        """
        Generate options for navigator.credentials.create()
        """
        # Get existing credentials to exclude them (prevent re-registration)
        # We need byte credential_ids
        # ... logic skipped for simplicity in MVP, or implement list_credentials mapping
        
        # User entity also needs kwargs likely
        user = PublicKeyCredentialUserEntity(id=user_id.encode('utf-8'), name=username, display_name=username)
        
        options, state = WebAuthnManager.server.register_begin(
            user,
            credentials=[], # list of AuthenticatorData or credential IDs to exclude
            user_verification="discouraged", # 'preferred' or 'required'
            authenticator_attachment=None # 'platform' or 'cross-platform'
        )
        
        return options, state

    @staticmethod
    def verify_registration(username: str, response_data, state):
        """
        Verify the registration response
        """
        try:
            auth_data = WebAuthnManager.server.register_complete(
                state,
                response_data
            )
            
            # Save credential
            credential_id = auth_data.credential_data.credential_id
            
            # public_key is a COSEKey object in fido2 > 1.0, need to serialize
            from fido2 import cbor
            if not isinstance(auth_data.credential_data.public_key, bytes):
                public_key = cbor.encode(auth_data.credential_data.public_key)
            else:
                public_key = auth_data.credential_data.public_key
                
            sign_count = auth_data.counter
            
            # Helper: Determine transports if available in response
            transports = response_data.get('response', {}).get('transports', [])
            
            # Add to DB
            success, msg = WebAuthnDatabase.add_credential(
                user_id=username, # Using username as ID for simplicity
                credential_id=credential_id,
                public_key=public_key,
                sign_count=auth_data.counter,
                name=f"Key - {datetime.now().strftime('%Y-%m-%d')}", # Default name
                transports=transports
            )
            return success, msg
            
        except Exception as e:
            logger.error(f"WebAuthn registration failed: {e}")
            return False, str(e)
            
    @staticmethod
    def generate_authentication_options(username: str):
        """
        Generate options for navigator.credentials.get()
        """
        # Get user credentials
        creds = WebAuthnDatabase.list_credentials(username)
        if not creds:
             return None, "No credentials found"
            
        # Convert DB credentials to FIDO2 Lib objects
        from fido2.webauthn import AttestedCredentialData
        fido_creds = []
        
        print(f"[DEBUG] Creds Type: {type(creds)}")
        print(f"[DEBUG] Creds Content: {creds}")
        if creds and isinstance(creds[0], (bytes, int, str)):
             # It seems we might have gotten a single row/tuple instead of list of rows?
             # Or iterating over a Row object?
             print("[DEBUG] WARNING: Creds seems to be a single row/tuple!")
             
        for c in creds:
             print(f"[DEBUG] Processing cred: {type(c)} - {c}")
             try:
                 # AttestedCredentialData.create(aaguid, credential_id, public_key)
                 # public_key from DB is bytes (COSE), but create() expects decoded object (dict-like)
                 # or it expects bytes if it's the raw constructor? No, create() parses arguments.
                 # The error 'bytes object has no attribute get' suggests it tries to access fields on public_key.
                 # So we MUST decode it first.
                 
                 from fido2 import cbor
                 
                 pk_obj = c['public_key']
                 if isinstance(pk_obj, bytes):
                     try:
                        pk_obj = cbor.decode(pk_obj)
                     except Exception as e:
                        logger.error(f"Failed to decode public key CBOR: {e}")
                        # Fallback or skip? If we can't decode, we can't use it.
                        continue
                 
                 ac = AttestedCredentialData.create(
                     b'\x00'*16, # AAGUID
                     c['credential_id'],
                     pk_obj
                 )
                 fido_creds.append(ac)
             except Exception as e:
                 logger.error(f"Error recreating credential data: {e}")
                 # Skip invalid credentials
                 continue

        options, state = WebAuthnManager.server.authenticate_begin(fido_creds)
        
        print(f"[DEBUG] FIDO2 Options Type: {type(options)}")
        print(f"[DEBUG] FIDO2 Options Dir: {dir(options)}")
        
        # Serialize options to JSON-compatible dict explicitly
        # fido2 objects might not convert to dict() as expected or use camelCase keys
        
        # Check if options is wrapped (CredentialRequestOptions -> public_key)
        pk_options = getattr(options, 'public_key', options)
        
        opt_dict = {
            "challenge": websafe_encode(pk_options.challenge),
            "rpId": pk_options.rp_id,
            "timeout": pk_options.timeout,
            "userVerification": pk_options.user_verification,
        }
        
        if pk_options.allow_credentials:
            res_creds = []
            for c in pk_options.allow_credentials:
                res_creds.append({
                    "type": c.type,
                    "id": websafe_encode(c.id),
                    # "transports": c.transports # Removing transport hint to be more permissive
                })
            opt_dict["allowCredentials"] = res_creds

        return opt_dict, state

    @staticmethod
    def verify_authentication(username: str, response_data, state):
        """
        Verify authentication response
        """
        try:
            # We need the credential object that was used?
            # authenticate_complete returns the credential_data that matched?
            # It updates the counter.
            
            # We need to look up which credential was used based on ID in response
            cred_id_used = websafe_decode(response_data['id'])
            
            # Get stored credential
            stored_cred = WebAuthnDatabase.get_credential_by_id(cred_id_used)
            if not stored_cred:
                return False, "Unknown credential"
            
            # Check user mismatch?
            if stored_cred['user_id'] != username:
                return False, "Credential does not belong to user"

            from fido2.webauthn import AttestedCredentialData
            # sign_count from DB
            from fido2 import cbor
            # Ensure we wrap public_key correctly if needed by AttestedCredentialData constructor 
            # (it expects bytes usually, which stored_cred['public_key'] is)
            
            pk_obj = stored_cred['public_key']
            if isinstance(pk_obj, bytes):
                try:
                    pk_obj = cbor.decode(pk_obj)
                except Exception as e:
                    logger.error(f"Failed to decode public key CBOR during verify: {e}")
                    return False, "Invalid credential data"

            credential_data = AttestedCredentialData.create(
                b'\x00'*16, # AAGUID placeholder
                stored_cred['credential_id'],
                pk_obj, # Decoded COSEKey
            )
            
            # Verify
            # authenticate_complete returns the credential object that was used (AttestedCredentialData)
            # It does NOT return the new counter. We must extract it from authenticatorData.
            matched_cred = WebAuthnManager.server.authenticate_complete(
                state,
                [credential_data], # List of candidate credentials
                response_data
            )
            
            # Extract counter from response authenticatorData manually
            # AuthenticatorData layout: 32B (rpIdHash) + 1B (flags) + 4B (signCount) + ...
            import struct
            auth_data_bytes = websafe_decode(response_data['response']['authenticatorData'])
            if len(auth_data_bytes) < 37:
                return False, "Malformed authenticatorData"
                
            new_sign_count = struct.unpack('>I', auth_data_bytes[33:37])[0]
            
            # Check for counter rollback (cloned key protection)
            # Note: stored_cred['sign_count'] might be None/0
            current_count = stored_cred['sign_count'] or 0
            if new_sign_count <= current_count and new_sign_count != 0 and current_count != 0:
                logger.warning(f"Sign count rollback: stored={current_count}, new={new_sign_count}")
                return False, "Invalid signature counter"
            
            # Update counter in DB
            WebAuthnDatabase.update_sign_count(stored_cred['id'], new_sign_count)
            
            return True, "Authenticated"
            
        except Exception as e:
            logger.error(f"WebAuthn authentication failed: {e}")
            return False, str(e)
from datetime import datetime
