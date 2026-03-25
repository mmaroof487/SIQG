import json
import urllib.request
import urllib.error

BASE_URL = "http://localhost:8000"

# 1. Register
print("1. Registering user...")
register_data = {
    "username": "testuser",
    "email": "test@example.com",
    "password": "TestPassword123"
}
req = urllib.request.Request(
    f"{BASE_URL}/api/v1/auth/register",
    data=json.dumps(register_data).encode(),
    headers={"Content-Type": "application/json"}
)
try:
    response = urllib.request.urlopen(req)
    result = json.loads(response.read().decode())
    token = result.get("access_token")
    print(f"✅ Registered! Token: {token[:20]}...")
except urllib.error.HTTPError as e:
    print(f"Registration error: {e.read().decode()}")
    token = None

# 2. Login
if not token:
    print("\n2. Logging in...")
    login_data = {
        "username": "testuser",
        "password": "TestPassword123"
    }
    req = urllib.request.Request(
        f"{BASE_URL}/api/v1/auth/login",
        data=json.dumps(login_data).encode(),
        headers={"Content-Type": "application/json"}
    )
    try:
        response = urllib.request.urlopen(req)
        result = json.loads(response.read().decode())
        token = result.get("access_token")
        print(f"✅ Logged in! Token: {token[:20]}...")
    except urllib.error.HTTPError as e:
        print(f"Login error: {e.read().decode()}")
        exit(1)

# 3. Execute a query
print("\n3. Executing query...")
query_data = {"query": "SELECT 1 as test"}
req = urllib.request.Request(
    f"{BASE_URL}/api/v1/query/execute",
    data=json.dumps(query_data).encode(),
    headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
)
try:
    response = urllib.request.urlopen(req)
    result = json.loads(response.read().decode())
    print(f"✅ Query executed!")
    print(json.dumps(result, indent=2))
except urllib.error.HTTPError as e:
    print(f"Query error: {e.read().decode()}")
