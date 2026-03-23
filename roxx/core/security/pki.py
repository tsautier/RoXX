import os
from pathlib import Path
from datetime import datetime, timedelta
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

class PKIManager:
    """
    Embedded PKI Management.
    Handles internal CA generation and certificate issuance.
    """
    
    @staticmethod
    def get_pki_dir() -> Path:
        from roxx.utils.system import SystemManager
        pki_dir = SystemManager.get_config_dir() / "pki"
        pki_dir.mkdir(parents=True, exist_ok=True)
        return pki_dir

    @classmethod
    def create_ca(cls, common_name: str = "RoXX Internal CA") -> bool:
        """Generates a self-signed Root CA"""
        pki_dir = cls.get_pki_dir()
        ca_key_path = pki_dir / "ca.key"
        ca_cert_path = pki_dir / "ca.crt"
        
        if ca_cert_path.exists():
            return False # CA already exists
            
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=4096,
            backend=default_backend()
        )
        
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, u"FR"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"Paris"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, u"Paris"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"RoXX Security"),
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        ])
        
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.utcnow()
        ).not_valid_after(
            datetime.utcnow() + timedelta(days=3650) # 10 years
        ).add_extension(
            x509.BasicConstraints(ca=True, path_length=None), critical=True,
        ).sign(private_key, hashes.SHA256(), default_backend())
        
        # Save key
        with open(ca_key_path, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            ))
            
        # Save cert
        with open(ca_cert_path, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
            
        return True

    @classmethod
    def get_ca_status(cls) -> dict:
        pki_dir = cls.get_pki_dir()
        ca_crt = pki_dir / "ca.crt"
        return {
            "exists": ca_crt.exists(),
            "path": str(ca_crt) if ca_crt.exists() else None
        }

    @classmethod
    def list_certificates(cls) -> list:
        pki_dir = cls.get_pki_dir()
        certs = []
        for f in pki_dir.glob("*.crt"):
            if f.name == "ca.crt": continue
            certs.append({
                "name": f.stem,
                "path": str(f),
                "created": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            })
        return certs
