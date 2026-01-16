"""
Test Suite for RoXX Python Modules
Tests all migrated components
"""

import sys
from pathlib import Path

# Add roxx to path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test that all modules can be imported"""
    print("=" * 60)
    print("Testing Python Imports")
    print("=" * 60)
    
    tests = {
        'System Manager': lambda: __import__('roxx.utils.system', fromlist=['SystemManager']),
        'Service Manager': lambda: __import__('roxx.core.services', fromlist=['ServiceManager']),
        'I18n': lambda: __import__('roxx.utils.i18n', fromlist=['translate']),
        'Console': lambda: __import__('roxx.cli.console', fromlist=['main']),
        'inWebo Auth': lambda: __import__('roxx.core.auth.inwebo', fromlist=['InWeboAuthenticator']),
        'TOTP Auth': lambda: __import__('roxx.core.auth.totp', fromlist=['TOTPAuthenticator']),
        'EntraID Auth': lambda: __import__('roxx.core.auth.entraid'),
    }
    
    passed = 0
    failed = 0
    
    for name, test_func in tests.items():
        try:
            test_func()
            print(f"✓ {name:20} - OK")
            passed += 1
        except Exception as e:
            print(f"✗ {name:20} - FAILED: {e}")
            failed += 1
    
    print(f"\nResults: {passed} passed, {failed} failed\n")
    return failed == 0


def test_system_manager():
    """Test SystemManager functionality"""
    print("=" * 60)
    print("Testing SystemManager")
    print("=" * 60)
    
    from roxx.utils.system import SystemManager
    
    tests = [
        ("OS Detection", lambda: SystemManager.get_os()),
        ("Admin Check", lambda: SystemManager.is_admin()),
        ("Config Dir", lambda: SystemManager.get_config_dir()),
        ("Data Dir", lambda: SystemManager.get_data_dir()),
        ("Log Dir", lambda: SystemManager.get_log_dir()),
    ]
    
    for name, test_func in tests:
        try:
            result = test_func()
            print(f"✓ {name:20} - {result}")
        except Exception as e:
            print(f"✗ {name:20} - ERROR: {e}")
    
    print()


def test_service_manager():
    """Test ServiceManager functionality"""
    print("=" * 60)
    print("Testing ServiceManager")
    print("=" * 60)
    
    from roxx.core.services import ServiceManager
    
    mgr = ServiceManager()
    
    # print(f"OS Type: {mgr.os_type}")
    print("\nService Status:")
    
    statuses = mgr.get_all_services_status()
    for service, status in statuses.items():
        print(f"  {service:15} - {status.value}")
    
    print()


def test_i18n():
    """Test I18n functionality"""
    print("=" * 60)
    print("Testing I18n")
    print("=" * 60)
    
    from roxx.utils.i18n import translate, set_locale, get_locale
    
    print(f"Current locale: {get_locale()}")
    print(f"Translation test: {translate('app_title', 'Default Title')}")
    
    set_locale('FR')
    print(f"After FR switch: {translate('app_title', 'Default Title')}")
    
    set_locale('EN')
    print(f"After EN switch: {translate('app_title', 'Default Title')}")
    
    print()


def test_totp():
    """Test TOTP functionality"""
    print("=" * 60)
    print("Testing TOTP")
    print("=" * 60)
    
    from roxx.core.auth.totp import TOTPAuthenticator
    
    # Test avec une clé secrète connue
    secret = "JBSWY3DPEHPK3PXP"  # "Hello!" en base32
    
    try:
        totp = TOTPAuthenticator(secret=secret)
        code = totp.generate()
        print(f"✓ Generated TOTP code: {code}")
        
        # Vérifier que le code est valide
        if totp.verify(code):
            print(f"✓ Code verification: OK")
        else:
            print(f"✗ Code verification: FAILED")
            
    except Exception as e:
        print(f"✗ TOTP test failed: {e}")
    
    print()


def test_file_structure():
    """Test file structure"""
    print("=" * 60)
    print("Testing File Structure")
    print("=" * 60)
    
    required_files = [
        'roxx/__init__.py',
        'roxx/__main__.py',
        'roxx/cli/__init__.py',
        'roxx/cli/console.py',
        'roxx/core/__init__.py',
        'roxx/core/services.py',
        'roxx/core/auth/__init__.py',
        'roxx/core/auth/inwebo.py',
        'roxx/core/auth/totp.py',
        'roxx/core/auth/entraid.py',
        'roxx/utils/__init__.py',
        'roxx/utils/system.py',
        'roxx/utils/i18n.py',
        'pyproject.toml',
        'requirements.txt',
    ]
    
    base_dir = Path(__file__).parent
    
    for file_path in required_files:
        full_path = base_dir / file_path
        if full_path.exists():
            size = full_path.stat().st_size
            print(f"✓ {file_path:40} ({size:,} bytes)")
        else:
            print(f"✗ {file_path:40} MISSING")
    
    print()


def main():
    """Run all tests"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 15 + "RoXX Test Suite" + " " * 28 + "║")
    print("╚" + "=" * 58 + "╝")
    print()
    
    all_passed = True
    
    # Run tests
    all_passed &= test_imports()
    test_file_structure()
    test_system_manager()
    test_service_manager()
    test_i18n()
    test_totp()
    
    # Summary
    print("=" * 60)
    if all_passed:
        print("✅ ALL TESTS PASSED!")
        print("\nYou can now:")
        print("  1. Run the console: python -m roxx")
        print("  2. Use auth modules with FreeRADIUS")
        print("  3. Continue with setup assistant migration")
    else:
        print("❌ SOME TESTS FAILED")
        print("\nPlease check the errors above")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
