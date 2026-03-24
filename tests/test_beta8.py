"""
Tests for RoXX 1.0.0-beta8 Features
Tests RBAC, Multi-tenant, Duo/Okta providers, and Cache optimizations
"""

import sys
import os
import sqlite3
import tempfile
import time
from pathlib import Path

# Add roxx to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_rbac_module():
    """Test RBAC module basics"""
    print("=" * 60)
    print("Testing RBAC Module")
    print("=" * 60)

    from roxx.core.auth.rbac import Role, check_permission, Action, ROLE_PERMISSIONS

    passed = 0
    failed = 0

    # Test role enum
    try:
        assert Role.SUPERADMIN == "superadmin"
        assert Role.ADMIN == "admin"
        assert Role.AUDITOR == "auditor"
        print(f"✓ Role enum values OK")
        passed += 1
    except AssertionError as e:
        print(f"✗ Role enum: {e}")
        failed += 1

    # Test superadmin has all permissions
    try:
        for action in [Action.MANAGE_ADMINS, Action.CHANGE_ROLES, Action.DELETE_ADMINS,
                       Action.MANAGE_SYSTEM_CONFIG, Action.VIEW_DASHBOARD, Action.MANAGE_TENANTS]:
            assert check_permission(Role.SUPERADMIN, action), f"Superadmin missing {action}"
        print(f"✓ Superadmin has all permissions")
        passed += 1
    except AssertionError as e:
        print(f"✗ Superadmin permissions: {e}")
        failed += 1

    # Test admin cannot change roles or delete
    try:
        assert not check_permission(Role.ADMIN, Action.CHANGE_ROLES)
        assert not check_permission(Role.ADMIN, Action.DELETE_ADMINS)
        assert not check_permission(Role.ADMIN, Action.MANAGE_TENANTS)
        assert check_permission(Role.ADMIN, Action.MANAGE_RADIUS_USERS)
        print(f"✓ Admin role restrictions OK")
        passed += 1
    except AssertionError as e:
        print(f"✗ Admin restrictions: {e}")
        failed += 1

    # Test auditor is read-only
    try:
        assert check_permission(Role.AUDITOR, Action.VIEW_DASHBOARD)
        assert check_permission(Role.AUDITOR, Action.VIEW_LOGS)
        assert not check_permission(Role.AUDITOR, Action.MANAGE_ADMINS)
        assert not check_permission(Role.AUDITOR, Action.MANAGE_RADIUS_USERS)
        assert not check_permission(Role.AUDITOR, Action.MANAGE_SYSTEM_CONFIG)
        print(f"✓ Auditor read-only restrictions OK")
        passed += 1
    except AssertionError as e:
        print(f"✗ Auditor restrictions: {e}")
        failed += 1

    print(f"\nRBAC Results: {passed} passed, {failed} failed\n")
    return failed == 0


def test_tenant_db():
    """Test Tenant Database CRUD"""
    print("=" * 60)
    print("Testing Tenant Database")
    print("=" * 60)

    from roxx.core.auth.tenant_db import TenantDatabase

    # Use temp DB
    import roxx.core.auth.tenant_db as tdb
    old_path = tdb.DB_PATH
    tdb.DB_PATH = Path(tempfile.mktemp(suffix='.db'))

    passed = 0
    failed = 0

    try:
        TenantDatabase.init()
        print("✓ Init OK")
        passed += 1

        # Create tenant
        ok, msg, tid = TenantDatabase.create_tenant("Acme Corp", "acme", "Test tenant")
        assert ok and tid is not None, f"Create failed: {msg}"
        print(f"✓ Create tenant OK (ID: {tid})")
        passed += 1

        # Duplicate slug
        ok2, msg2, _ = TenantDatabase.create_tenant("Acme 2", "acme", "Dup")
        assert not ok2, "Duplicate slug should fail"
        print(f"✓ Duplicate slug rejected OK")
        passed += 1

        # List tenants
        tenants = TenantDatabase.list_tenants()
        assert len(tenants) == 1
        assert tenants[0]['name'] == 'Acme Corp'
        print(f"✓ List tenants OK ({len(tenants)} found)")
        passed += 1

        # Get by slug
        t = TenantDatabase.get_tenant_by_slug("acme")
        assert t and t['name'] == 'Acme Corp'
        print(f"✓ Get by slug OK")
        passed += 1

        # Assign admin
        ok, msg = TenantDatabase.assign_admin("admin", tid)
        assert ok
        admins = TenantDatabase.get_tenant_admins(tid)
        assert "admin" in admins
        print(f"✓ Assign admin OK")
        passed += 1

        # Get admin tenants
        admin_t = TenantDatabase.get_admin_tenants("admin")
        assert len(admin_t) == 1
        print(f"✓ Get admin tenants OK")
        passed += 1

        # Delete
        ok, msg = TenantDatabase.delete_tenant(tid)
        assert ok
        tenants = TenantDatabase.list_tenants()
        assert len(tenants) == 0
        print(f"✓ Delete tenant OK")
        passed += 1

    except Exception as e:
        print(f"✗ Error: {e}")
        failed += 1
    finally:
        tdb.DB_PATH = old_path

    print(f"\nTenant Results: {passed} passed, {failed} failed\n")
    return failed == 0


def test_duo_provider():
    """Test Duo Provider instantiation and signing"""
    print("=" * 60)
    print("Testing Duo Provider")
    print("=" * 60)

    from roxx.core.auth.duo import DuoProvider

    passed = 0
    failed = 0

    try:
        duo = DuoProvider({
            'integration_key': 'DIXXXXXXXXXXXXXXXXXX',
            'secret_key': 'deadbeef01234567890abcdef01234567890abcd',
            'api_hostname': 'api-test.duosecurity.com'
        })

        # Verify object creation
        assert duo.ikey == 'DIXXXXXXXXXXXXXXXXXX'
        assert duo.api_host == 'api-test.duosecurity.com'
        print("✓ DuoProvider instantiation OK")
        passed += 1

        # Test signing (just verifies no error)
        headers = duo._sign_request("POST", "/auth/v2/preauth", {"username": "test"})
        assert "Authorization" in headers
        assert "Date" in headers
        assert headers["Authorization"].startswith("Basic ")
        print("✓ HMAC-SHA1 request signing OK")
        passed += 1

    except Exception as e:
        print(f"✗ Duo test error: {e}")
        failed += 1

    print(f"\nDuo Results: {passed} passed, {failed} failed\n")
    return failed == 0


def test_okta_provider():
    """Test Okta Provider instantiation"""
    print("=" * 60)
    print("Testing Okta Provider")
    print("=" * 60)

    from roxx.core.auth.okta import OktaProvider

    passed = 0
    failed = 0

    try:
        okta = OktaProvider({
            'org_url': 'https://dev-test.okta.com',
            'api_token': 'faketoken123'
        })

        assert okta.org_url == 'https://dev-test.okta.com'
        assert 'Authorization' in okta._headers
        assert okta._headers['Authorization'] == 'SSWS faketoken123'
        print("✓ OktaProvider instantiation OK")
        passed += 1

    except Exception as e:
        print(f"✗ Okta test error: {e}")
        failed += 1

    print(f"\nOkta Results: {passed} passed, {failed} failed\n")
    return failed == 0


def test_cache_lru():
    """Test improved AuthCache with LRU"""
    print("=" * 60)
    print("Testing AuthCache (LRU)")
    print("=" * 60)

    from roxx.core.radius_backends.cache import AuthCache

    passed = 0
    failed = 0

    # Test LRU eviction
    try:
        cache = AuthCache(ttl=10, max_size=3)

        cache.set("user1", "pass1", {"attr": "a"})
        cache.set("user2", "pass2", {"attr": "b"})
        cache.set("user3", "pass3", {"attr": "c"})

        # Cache full (3/3), adding user4 should evict user1 (oldest)
        cache.set("user4", "pass4", {"attr": "d"})

        assert cache.get("user1", "pass1") is None, "user1 should be evicted"
        assert cache.get("user2", "pass2") is not None, "user2 should exist"
        print("✓ LRU eviction OK")
        passed += 1
    except AssertionError as e:
        print(f"✗ LRU eviction: {e}")
        failed += 1

    # Test TTL expiry
    try:
        cache2 = AuthCache(ttl=1, max_size=100)
        cache2.set("ttluser", "pass", {"attr": "x"})
        result = cache2.get("ttluser", "pass")
        assert result is not None, "Should be cached"

        time.sleep(1.5)
        result = cache2.get("ttluser", "pass")
        assert result is None, "Should be expired"
        print("✓ TTL expiry OK")
        passed += 1
    except AssertionError as e:
        print(f"✗ TTL expiry: {e}")
        failed += 1

    # Test stats
    try:
        cache3 = AuthCache(ttl=10, max_size=10)
        cache3.set("statuser", "pass", {})
        cache3.get("statuser", "pass")  # hit
        cache3.get("nobody", "x")  # miss

        stats = cache3.stats()
        assert stats['hits'] >= 1
        assert stats['misses'] >= 1
        assert 'evictions' in stats
        assert 'total_gets' in stats
        print(f"✓ Stats OK (hits={stats['hits']}, misses={stats['misses']}, evictions={stats['evictions']})")
        passed += 1
    except AssertionError as e:
        print(f"✗ Stats: {e}")
        failed += 1

    print(f"\nCache Results: {passed} passed, {failed} failed\n")
    return failed == 0


def test_connection_pool():
    """Test ConnectionPool"""
    print("=" * 60)
    print("Testing Connection Pool")
    print("=" * 60)

    from roxx.core.radius_backends.pool import ConnectionPool, PooledConnection

    passed = 0
    failed = 0

    # Simple mock connection
    class MockConn:
        def __init__(self):
            self.closed = False
        def close(self):
            self.closed = True

    try:
        pool = ConnectionPool(
            create_func=MockConn,
            close_func=lambda c: c.close(),
            health_check_func=lambda c: not c.closed,
            pool_size=3,
            timeout=5.0
        )

        stats = pool.stats()
        assert stats['pool_size'] == 3
        assert stats['available'] == 2  # warmup creates 2
        print(f"✓ Pool init OK (available={stats['available']})")
        passed += 1

        # Acquire and release
        conn1 = pool.acquire()
        assert conn1 is not None
        stats = pool.stats()
        assert stats['in_use'] == 1
        pool.release(conn1)
        stats = pool.stats()
        assert stats['in_use'] == 0
        print("✓ Acquire/release OK")
        passed += 1

        # Context manager
        with PooledConnection(pool) as conn:
            assert conn is not None
        stats = pool.stats()
        assert stats['in_use'] == 0
        print("✓ Context manager OK")
        passed += 1

        pool.close_all()
        print("✓ Close all OK")
        passed += 1

    except Exception as e:
        print(f"✗ Pool error: {e}")
        import traceback
        traceback.print_exc()
        failed += 1

    print(f"\nPool Results: {passed} passed, {failed} failed\n")
    return failed == 0


def test_admin_roles():
    """Test AdminDatabase role methods"""
    print("=" * 60)
    print("Testing Admin Role DB Methods")
    print("=" * 60)

    from roxx.core.auth.db import AdminDatabase

    # Use temp DB
    import roxx.core.auth.db as adb
    old_path = adb._DEFAULT_DB_PATH
    temp_path = Path(tempfile.mktemp(suffix='.db'))
    adb._DEFAULT_DB_PATH = temp_path
    adb.DB_PATH = temp_path

    passed = 0
    failed = 0

    try:
        AdminDatabase.init_db()

        # Insert a test admin manually
        conn = sqlite3.connect(temp_path)
        conn.execute("""INSERT INTO admins (username, password_hash, role) 
                       VALUES ('testadmin', 'fakehash', 'admin')""")
        conn.commit()
        conn.close()

        # Get role
        role = AdminDatabase.get_role('testadmin')
        assert role == 'admin', f"Expected 'admin', got '{role}'"
        print("✓ get_role OK")
        passed += 1

        # Set role
        ok = AdminDatabase.set_role('testadmin', 'superadmin')
        assert ok
        role = AdminDatabase.get_role('testadmin')
        assert role == 'superadmin', f"Expected 'superadmin', got '{role}'"
        print("✓ set_role OK")
        passed += 1

        # Invalid role
        ok = AdminDatabase.set_role('testadmin', 'invalid_role')
        assert not ok
        print("✓ Invalid role rejected OK")
        passed += 1

        # Non-existent user
        role = AdminDatabase.get_role('nonexistent')
        assert role == 'admin', f"Default should be 'admin', got '{role}'"
        print("✓ Default role for unknown user OK")
        passed += 1

    except Exception as e:
        print(f"✗ Admin role error: {e}")
        import traceback
        traceback.print_exc()
        failed += 1
    finally:
        adb._DEFAULT_DB_PATH = old_path
        adb.DB_PATH = old_path
        if temp_path.exists():
            temp_path.unlink()

    print(f"\nAdmin Role Results: {passed} passed, {failed} failed\n")
    return failed == 0


def main():
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "RoXX 1.0.0-beta8 Test Suite" + " " * 21 + "║")
    print("╚" + "=" * 58 + "╝")
    print()

    results = {
        "RBAC Module": test_rbac_module(),
        "Admin Roles DB": test_admin_roles(),
        "Tenant Database": test_tenant_db(),
        "Duo Provider": test_duo_provider(),
        "Okta Provider": test_okta_provider(),
        "Auth Cache (LRU)": test_cache_lru(),
        "Connection Pool": test_connection_pool(),
    }

    print("=" * 60)
    print("Summary:")
    all_passed = True
    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {name:25} {status}")
        if not passed:
            all_passed = False

    print("=" * 60)
    if all_passed:
        print("✅ ALL BETA8 TESTS PASSED!")
    else:
        print("❌ SOME TESTS FAILED")
    print()
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
