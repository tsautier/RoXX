import os
import ssl
from pathlib import Path
from typing import Tuple, Optional
import shutil
from datetime import datetime, timedelta
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
import ipaddress
import socket

class CertManager:
    """
    Manages SSL certificates for the application.
    Stores certificates in <config_dir>/certs/
    Expects 'server.crt' and 'server.key'.
    """
    
    CERT_DIR_NAME = "certs"
    CERT_FILENAME = "server.crt"
    KEY_FILENAME = "server.key"

    @classmethod
    def get_cert_dir(cls) -> Path:
        from roxx.utils.system import SystemManager
        cert_dir = SystemManager.get_config_dir() / cls.CERT_DIR_NAME
        cert_dir.mkdir(parents=True, exist_ok=True)
        return cert_dir

    @classmethod
    def get_cert_paths(cls) -> Tuple[Path, Path]:
        cert_dir = cls.get_cert_dir()
        return (cert_dir / cls.CERT_FILENAME), (cert_dir / cls.KEY_FILENAME)

    @classmethod
    def get_status(cls) -> dict:
        cert_path, key_path = cls.get_cert_paths()
        
        status = {
            "enabled": False,
            "cert_exists": cert_path.exists(),
            "key_exists": key_path.exists(),
            "details": {}
        }

        if status["cert_exists"] and status["key_exists"]:
            try:
                # Basic validation: Check if loadable
                context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
                context.load_cert_chain(certfile=str(cert_path), keyfile=str(key_path))
                status["enabled"] = True
                
                # Extract some info (requires cryptography or parsing, let's keep it simple for now or use ssl module)
                # We can read the cert file to get issuer/expiry if we want to parse it.
                # For now just confirming it loads is enough for "Active".
                status["details"] = {"message": "Certificate is valid and loadable."}
                
            except Exception as e:
                status["valid"] = False
                status["error"] = str(e)
        
        return status

    @classmethod
    def upload_cert(cls, cert_content: str, key_content: str) -> Tuple[bool, str]:
        """
        Saves certificate content to files. 
        Validates that they match and are valid SSL files.
        """
        cert_dir = cls.get_cert_dir()
        temp_cert = cert_dir / "temp.crt"
        temp_key = cert_dir / "temp.key"
        
        try:
            # Save temp
            with open(temp_cert, 'w') as f:
                f.write(cert_content)
            with open(temp_key, 'w') as f:
                f.write(key_content)
                
            # Validate
            context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            context.load_cert_chain(certfile=str(temp_cert), keyfile=str(temp_key))
            
            # If valid, rename to actual
            shutil.move(str(temp_cert), str(cert_dir / cls.CERT_FILENAME))
            shutil.move(str(temp_key), str(cert_dir / cls.KEY_FILENAME))
            
            return True, "Certificate uploaded and verified successfully."
            
        except Exception as e:
            # Cleanup temp
            if temp_cert.exists(): os.remove(temp_cert)
            if temp_key.exists(): os.remove(temp_key)
            return False, f"Invalid certificate pair: {str(e)}"

    @classmethod
    def generate_self_signed_cert(cls, hostname: str = None) -> Tuple[bool, str]:
        """
        Generates a self-signed certificate for local development/beta.
        Automatically adds localhost and local IP to SAN.
        """
        cert_path, key_path = cls.get_cert_paths()
        
        if not hostname:
            hostname = socket.gethostname()

        try:
            # Generate key
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )
            
            # Subject and Issuer (Self-signed)
            subject = issuer = x509.Name([
                x509.NameAttribute(NameOID.COUNTRY_NAME, u"FR"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"RoXX Security (Auto-Generated)"),
                x509.NameAttribute(NameOID.COMMON_NAME, hostname),
            ])
            
            # SAN (Subject Alternative Name) - crucial for modern browsers
            sans = [
                x509.DNSName(u"localhost"),
                x509.DNSName(hostname),
                x509.IPAddress(ipaddress.IPv4Address(u"127.0.0.1")),
            ]
            
            # Try to get local IP
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                s.close()
                sans.append(x509.IPAddress(ipaddress.IPv4Address(local_ip)))
            except:
                pass

            cert = x509.CertificateBuilder().subject_name(
                subject
            ).issuer_name(
                issuer
            ).public_key(
                private_key.public_key()
            ).serial_number(
                x509.random_serial_number()
            ).not_valid_before(
                datetime.utcnow() - timedelta(minutes=1)
            ).not_valid_after(
                datetime.utcnow() + timedelta(days=365)
            ).add_extension(
                x509.SubjectAlternativeName(sans),
                critical=False,
            ).sign(private_key, hashes.SHA256(), default_backend())
            
            # Save files
            with open(key_path, "wb") as f:
                f.write(private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.TraditionalOpenSSL,
                    encryption_algorithm=serialization.NoEncryption()
                ))
                
            with open(cert_path, "wb") as f:
                f.write(cert.public_bytes(serialization.Encoding.PEM))
                
            return True, f"Self-signed certificate generated for {hostname}"
            
        except Exception as e:
            return False, f"Failed to generate certificate: {str(e)}"

            return True, "Certificate removed."
        except Exception as e:
            return False, str(e)

    @classmethod
    def get_ca_paths(cls) -> Path:
        """Returns path to ca_bundle.crt"""
        cert_dir = cls.get_cert_dir()
        return cert_dir / "ca_bundle.crt"

    @classmethod
    def upload_ca(cls, ca_content: str) -> Tuple[bool, str]:
        """Uploads a CA Bundle for client verification"""
        ca_path = cls.get_ca_paths()
        try:
             with open(ca_path, 'w') as f:
                 f.write(ca_content)
             return True, "CA Bundle uploaded successfully."
        except Exception as e:
            return False, str(e)

    @classmethod
    def remove_ca(cls) -> Tuple[bool, str]:
        ca_path = cls.get_ca_paths()
        try:
            if ca_path.exists(): os.remove(ca_path)
            return True, "CA Bundle removed."
        except Exception as e:
            return False, str(e)
