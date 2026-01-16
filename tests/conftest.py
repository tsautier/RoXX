"""
Pytest configuration for RoXX test suite
"""

import sys
from pathlib import Path

# Add roxx to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create a temporary configuration directory"""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    return config_dir


@pytest.fixture
def mock_certificates(tmp_path):
    """Create mock certificate files for testing"""
    cert_dir = tmp_path / "certs"
    cert_dir.mkdir()
    
    # Create dummy cert files
    cert_file = cert_dir / "test_cert.pem"
    key_file = cert_dir / "test_key.pem"
    
    cert_file.write_text("FAKE CERTIFICATE")
    key_file.write_text("FAKE KEY")
    
    return cert_file, key_file
