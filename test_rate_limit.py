
import requests
import time

URL = "http://localhost:8000/login"
# Assuming 'sitetech' user exists or just testing the hit count on the endpoint
DATA = {"username": "admin", "password": "wrongpassword"}

print(f"Testing rate limit on {URL}...")

for i in range(1, 8):
    try:
        response = requests.post(URL, data=DATA)
        print(f"Request {i}: Status {response.status_code}")
        if response.status_code == 429:
            print("✅ Rate limit triggered successfully (429 Too Many Requests)")
            break
    except Exception as e:
        print(f"Request {i} failed: {e}")
    
    time.sleep(0.5)
