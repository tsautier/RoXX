#!/usr/bin/env python3
"""
Quick test script for RoXX Python console
Run this to verify the installation
"""

import sys
from pathlib import Path

def check_dependencies():
    """Vérifie que toutes les dépendances sont installées"""
    required = {
        'rich': 'Interface TUI',
        'questionary': 'Prompts interactifs',
        'psutil': 'Informations système',
    }
    
    missing = []
    for package, desc in required.items():
        try:
            __import__(package)
            print(f"✓ {package:15} - {desc}")
        except ImportError:
            print(f"✗ {package:15} - {desc} [MISSING]")
            missing.append(package)
    
    if missing:
        print(f"\n❌ Missing packages: {', '.join(missing)}")
        print(f"\nInstall with: pip install {' '.join(missing)}")
        return False
    
    print("\n✅ All dependencies installed!")
    return True

def check_structure():
    """Vérifie la structure du projet"""
    required_files = [
        'roxx/__init__.py',
        'roxx/__main__.py',
        'roxx/cli/console.py',
        'roxx/core/services.py',
        'roxx/utils/system.py',
        'roxx/utils/i18n.py',
    ]
    
    print("\nChecking project structure...")
    all_exist = True
    
    for file in required_files:
        path = Path(file)
        if path.exists():
            print(f"✓ {file}")
        else:
            print(f"✗ {file} [MISSING]")
            all_exist = False
    
    if all_exist:
        print("\n✅ Project structure OK!")
    else:
        print("\n❌ Some files are missing!")
    
    return all_exist

def test_imports():
    """Test les imports Python"""
    print("\nTesting Python imports...")
    
    try:
        from roxx.utils.system import SystemManager
        from roxx.core.services import ServiceManager
        from roxx.utils.i18n import translate
        
        print("✓ SystemManager imported")
        print("✓ ServiceManager imported")
        print("✓ I18n imported")
        
        # Test basique
        os_type = SystemManager.get_os()
        print(f"\n✓ Detected OS: {os_type}")
        
        print("\n✅ All imports successful!")
        return True
    except Exception as e:
        print(f"\n❌ Import error: {e}")
        return False

def main():
    """Main test function"""
    print("=" * 60)
    print("RoXX Python Console - Installation Test")
    print("=" * 60)
    print()
    
    deps_ok = check_dependencies()
    struct_ok = check_structure()
    imports_ok = test_imports()
    
    print("\n" + "=" * 60)
    if deps_ok and struct_ok and imports_ok:
        print("✅ ALL TESTS PASSED!")
        print("\nYou can now run the console with:")
        print("  python -m roxx")
    else:
        print("❌ SOME TESTS FAILED")
        print("\nPlease fix the issues above before running the console.")
    print("=" * 60)

if __name__ == "__main__":
    main()
