#!/usr/bin/env python3
"""Quick test script for Phase 1 & 2 features."""

import requests
import json

BASE_URL = "http://localhost:8000"

def main():
    print("🔐 === PHASE 1 & 2 Testing ===\n")

    # 1. Register a user
    print("1️⃣ Registering test user...")
    reg_response = requests.post(
        f"{BASE_URL}/api/v1/auth/register",
        json={
            "username": "testuser",
            "email": "testuser@example.com",
            "password": "testpass123"
        }
    )

    if reg_response.status_code != 200:
        print(f"❌ Registration failed: {reg_response.json()}")
        return

    token = reg_response.json()["access_token"]
    print(f"✅ Registration successful\n")
    print(f"Token: {token[:30]}...\n")

    # Test SQL injection blocking
    print("2️⃣ Testing SQL Injection Detection (should be BLOCKED)...")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    response = requests.post(
        f"{BASE_URL}/api/v1/query/execute",
        headers=headers,
        json={"query": "SELECT * FROM users WHERE id = 1 OR 1=1"}
    )

    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}\n")

    # Test DROP TABLE blocking
    print("3️⃣ Testing DROP TABLE Blocking (should be BLOCKED)...")
    response = requests.post(
        f"{BASE_URL}/api/v1/query/execute",
        headers=headers,
        json={"query": "DROP TABLE users"}
    )

    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}\n")

    # Test valid SELECT
    print("4️⃣ Testing Valid SELECT Query (should WORK)...")
    response = requests.post(
        f"{BASE_URL}/api/v1/query/execute",
        headers=headers,
        json={"query": "SELECT 1 AS test"}
    )

    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        resp_json = response.json()
        print(f"✅ Query succeeded!")
        print(f"   Latency: {resp_json.get('latency_ms', 'N/A')}ms")
        print(f"   Cached: {resp_json.get('cached', 'N/A')}")
        print(f"   Cost: {resp_json.get('cost', 'N/A')}")
    else:
        print(f"❌ Query failed: {response.json()}\n")

    print("\n✨ Test Complete!")

if __name__ == "__main__":
    main()
