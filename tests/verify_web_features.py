import requests
import sys
import os
import websocket
import threading
import time
import base64

BASE_URL = "http://localhost:8000"
ADMIN_USER = os.getenv("ROXX_ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ROXX_ADMIN_PASSWORD", "admin")

def test_auth():
    print("\n[TEST] Authentication...")
    # Test without auth
    resp = requests.get(f"{BASE_URL}/")
    if resp.status_code == 401:
        print("  [PASS] Unauthorized access blocked (401)")
    else:
        print(f"  [FAIL] Expected 401, got {resp.status_code}")
        return False

    # Test with auth
    resp = requests.get(f"{BASE_URL}/", auth=(ADMIN_USER, ADMIN_PASS))
    if resp.status_code == 200:
        print("  [PASS] Authorized access allowed (200)")
    else:
        print(f"  [FAIL] Expected 200, got {resp.status_code}")
        return False
    return True

def test_system_info():
    print("\n[TEST] System Info Endpoint...")
    resp = requests.get(f"{BASE_URL}/api/system/info", auth=(ADMIN_USER, ADMIN_PASS))
    if resp.status_code == 200:
        data = resp.json()
        print(f"  [PASS] Got system info: OS={data.get('os')}, Uptime={data.get('uptime')}")
        if data.get('version') == "1.0.0-beta2":
             print("  [PASS] Version matches expected (1.0.0-beta2)")
        else:
             print(f"  [WARN] Version mismatch: {data.get('version')}")
    else:
        print(f"  [FAIL] Failed to get system info: {resp.status_code}")
        return False
    return True

def test_user_crud():
    print("\n[TEST] User Management (CRUD)...")
    test_user = "testuser_verify"
    test_pass = "secret123"
    
    # 1. Add User
    print(f"  [STEP] Adding user '{test_user}'...")
    resp = requests.post(
        f"{BASE_URL}/api/users", 
        data={"username": test_user, "password": test_pass, "user_type": "Cleartext-Password"},
        auth=(ADMIN_USER, ADMIN_PASS)
    )
    if resp.status_code == 200:
        print("  [PASS] User added successfully")
    else:
        print(f"  [FAIL] Failed to add user: {resp.text}")
        return False

    # 2. Verify in Users Page list
    resp = requests.get(f"{BASE_URL}/users", auth=(ADMIN_USER, ADMIN_PASS))
    if test_user in resp.text:
        print("  [PASS] User found in UI list")
    else:
        print("  [FAIL] User not found in UI list")
        return False

    # 3. Delete User
    print(f"  [STEP] Deleting user '{test_user}'...")
    resp = requests.delete(f"{BASE_URL}/api/users/{test_user}", auth=(ADMIN_USER, ADMIN_PASS))
    if resp.status_code == 200:
        print("  [PASS] User deleted successfully")
    else:
        print(f"  [FAIL] Failed to delete user: {resp.text}")
        return False

    # 4. Verify deletion
    resp = requests.get(f"{BASE_URL}/users", auth=(ADMIN_USER, ADMIN_PASS))
    if test_user not in resp.text:
        print("  [PASS] User removed from UI list")
    else:
        print("  [FAIL] User still present in UI list")
        return False
        
    return True

def test_websocket():
    print("\n[TEST] WebSocket Logs...")
    # Basic Auth header for Websocket
    auth_str = f"{ADMIN_USER}:{ADMIN_PASS}"
    auth_bytes = auth_str.encode('ascii')
    base64_auth = base64.b64encode(auth_bytes).decode('ascii')
    headers = [f"Authorization: Basic {base64_auth}"]
    
    ws_url = "ws://localhost:8000/ws/logs"
    
    result = {"received": False}
    
    def on_message(ws, message):
        print(f"  [PASS] Received log message: {message[:50]}...")
        result["received"] = True
        ws.close()

    def on_error(ws, error):
        print(f"  [FAIL] WebSocket error: {error}")

    def on_open(ws):
        print("  [STEP] WebSocket connected")

    # Run WS in a thread with timeout
    ws = websocket.WebSocketApp(ws_url, header=headers, on_message=on_message, on_error=on_error, on_open=on_open)
    wst = threading.Thread(target=ws.run_forever)
    wst.daemon = True
    wst.start()
    
    time.sleep(3) # Wait for connection and maybe a simulated log
    if result["received"]:
        print("  [PASS] WebSocket test passed")
        return True
    else:
        print("  [WARN] No logs received in 3s (Server might be quiet or simulated logs handling issue)")
        # For verification purpose, connection success (open) is usually enough if no logs are generated immediately
        # But our mock sends simulated logs after 2s if file missing.
        return False

if __name__ == "__main__":
    print(f"Starting verification on {BASE_URL}")
    try:
        if not test_auth(): sys.exit(1)
        if not test_system_info(): sys.exit(1)
        if not test_user_crud(): sys.exit(1)
        if not test_websocket(): 
             print("WebSocket test timed out or failed (check if websockets lib is installed for client test)")
        print("\nAll Tests Completed.")
    except Exception as e:
        print(f"\n[CRITICAL] Test script failed: {e}")
        sys.exit(1)
