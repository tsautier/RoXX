
import ssl
import hashlib
from typing import Optional, Dict

class CertAuthManager:
    """
    Handles logic for verifying client certificates from the request.
    """
    
    @staticmethod
    def get_cert_info(request) -> Optional[Dict]:
        """
        Extracts certificate info from the FastAPI/Starlette request object.
        Depends on Uvicorn SSL context.
        """
        try:
            transport = request.transport
            if not transport:
                return None
                
            ssl_object = transport.get_extra_info("ssl_object")
            if not ssl_object:
                return None
                
            cert = ssl_object.getpeercert()
            if not cert:
                return None
                
            # If cert is just binary (depending on SSL settings), we might need parsing.
            # Usually getpeercert() returns a dict if SSLSocket was created with cert_reqs=CERT_OPTIONAL/REQUIRED
            # AND ca_certs was provided.
            
            # Extract basic info
            subject = dict(x[0] for x in cert['subject'])
            issuer = dict(x[0] for x in cert['issuer'])
            
            # Calculate fingerprint (We need the DER binary for this, which getpeercert(binary_form=True) gives)
            # But getpeercert() returns either dict OR binary, not both easily without re-calling ?? 
            # Actually ssl_object.getpeercert(True) gives binary.
            
            der_cert = ssl_object.getpeercert(binary_form=True)
            fingerprint = hashlib.sha256(der_cert).hexdigest()
            
            return {
                "common_name": subject.get('commonName', 'Unknown'),
                "issuer": issuer.get('commonName', 'Unknown'),
                "fingerprint": fingerprint,
                "serial": cert.get('serialNumber')
            }
            
        except Exception as e:
            # print(f"Cert extraction error: {e}") # Debug only
            return None
            
    @staticmethod
    def verify_cert_ownership(username: str, cert_info: Dict) -> bool:
        """
        Verifies if the cert identified by fingerprint belongs to the user.
        """
        from roxx.core.auth.cert_db import CertDatabase
        stored_user = CertDatabase.get_user_by_fingerprint(cert_info['fingerprint'])
        return stored_user == username

