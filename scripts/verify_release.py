import asyncio
import httpx
import os
import time
import uuid

API_BASE = "http://localhost:8000/api/v1"

class ArgusVerifier:
    def __init__(self):
        self.results = {}
        self.client = httpx.AsyncClient(base_url=API_BASE, timeout=15.0)
        self.client2 = httpx.AsyncClient(base_url=API_BASE, timeout=15.0) # For User B
        
        self.users = {
            "A": {"username": f"user_a_{uuid.uuid4().hex[:6]}", "email": f"usera{uuid.uuid4().hex[:6]}@example.com", "password": "Password123", "role": "admin"},
            "B": {"username": f"user_b_{uuid.uuid4().hex[:6]}", "email": f"userb{uuid.uuid4().hex[:6]}@example.com", "password": "Password123", "role": "admin"}
        }
        self.db_strings = {
            "athletiq": "postgresql://argus:argus@postgres:5432/athleti_q",
            "fresh": "postgresql://argus:argus@postgres:5432/fresh_db",
            "invalid": "postgresql://wrong:wrong@postgres:5432/nope"
        }
        self.connection_ids = {}

    async def run_all(self):
        try:
            print("--- Starting Argus E2E Verification ---")
            await self.phase_0_env()
            await self.phase_1_auth()
            await self.phase_1_connections()
            await self.phase_1_5_isolation()
            await self.phase_2_security()
            await self.phase_3_5_concurrency()
            await self.phase_5_schema_intelligence()
            
            print("--- Finished ---")
            self.print_scorecard()
        finally:
            await self.client.aclose()
            await self.client2.aclose()

    def record(self, domain, name, passed, details=""):
        if domain not in self.results:
            self.results[domain] = {"passed": 0, "total": 0, "tests": []}
        self.results[domain]["total"] += 1
        if passed:
            self.results[domain]["passed"] += 1
        self.results[domain]["tests"].append({"name": name, "passed": passed, "details": details})
        status = "✅" if passed else "❌"
        # Print with truncated details if it's too long
        if len(details) > 100:
            details_str = details[:100] + "..."
        else:
            details_str = details
        print(f"[{domain}] {name}: {status} {details_str}")

    def print_scorecard(self):
        print("\n=== VERIFICATION SCORECARD ===")
        total_tests = 0
        total_passed = 0
        print(f"{'Area':<20} | {'Tests':<5} | {'Passed':<5}")
        print("-" * 35)
        for domain, stats in self.results.items():
            print(f"{domain:<20} | {stats['total']:<5} | {stats['passed']:<5}")
            total_tests += stats['total']
            total_passed += stats['passed']
        
        print("\nTotal Tests:", total_tests)
        print("Passed:", total_passed)
        print("Failed:", total_tests - total_passed)
        if total_tests > 0:
            print(f"Pass Rate: {(total_passed/total_tests)*100:.2f}%")

    async def phase_0_env(self):
        print("\n--- Phase 0: Environment Verification ---")
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get("http://localhost:8000/health", timeout=5.0)
            self.record("Environment", "API Reachable", resp.status_code == 200)
            if resp.status_code == 200:
                data = resp.json()
                self.record("Environment", "Redis Healthy", data.get("redis") == "ok")
                self.record("Environment", "PostgreSQL Primary Healthy", data.get("postgres_primary") == "ok" or data.get("db") == "ok")
        except Exception as e:
            self.record("Environment", "API Reachable", False, str(e))

    async def phase_1_auth(self):
        print("\n--- Phase 1: Authentication ---")
        # Register User A
        resp = await self.client.post("/auth/register", json=self.users["A"])
        self.record("Authentication", "Register User A", resp.status_code == 201 or resp.status_code == 200, resp.text)
        
        # Login User A
        resp = await self.client.post("/auth/login", json={"username": self.users["A"]["username"], "password": self.users["A"]["password"]})
        passed = resp.status_code == 200 and "argus_token" in resp.cookies
        self.record("Authentication", "Login User A (HttpOnly Cookie)", passed)
        if passed:
            token = resp.json().get("access_token")
            self.users["A"]["token"] = token
            self.client.headers["Authorization"] = f"Bearer {token}"

        # Register & Login User B
        await self.client2.post("/auth/register", json=self.users["B"])
        resp2 = await self.client2.post("/auth/login", json={"username": self.users["B"]["username"], "password": self.users["B"]["password"]})
        self.record("Authentication", "Login User B", resp2.status_code == 200)
        if resp2.status_code == 200:
            token = resp2.json().get("access_token")
            self.users["B"]["token"] = token
            self.client2.headers["Authorization"] = f"Bearer {token}"

        # Brute force lockout
        for i in range(6):
            r = await self.client.post("/auth/login", json={"username": "bruteforceuser", "password": "wrongpassword"})
            if r.status_code == 423 or r.status_code == 429: # Some lockout status code
                self.record("Authentication", "Brute Force Lockout", True)
                break
        else:
            self.record("Authentication", "Brute Force Lockout", False, "Did not lock out")

    async def phase_1_connections(self):
        print("\n--- Phase 1: Database Connections ---")
        # Save valid DB
        resp = await self.client.post("/connections", json={
            "display_name": "AthletIQ",
            "conn_str": self.db_strings["athletiq"],
            "db_type": "postgres"
        })
        passed = resp.status_code == 201 or resp.status_code == 200
        self.record("Connections", "Save valid DB (AthletIQ)", passed, resp.text)
        if passed:
            self.connection_ids["athletiq"] = resp.json()["id"]

        # Save Fresh DB
        resp = await self.client.post("/connections", json={
            "display_name": "Fresh DB",
            "conn_str": self.db_strings["fresh"],
            "db_type": "postgres"
        })
        if resp.status_code == 201 or resp.status_code == 200:
            self.connection_ids["fresh"] = resp.json()["id"]
        
        # Test connection (Valid)
        if "athletiq" in self.connection_ids:
            conn_id = self.connection_ids["athletiq"]
            resp = await self.client.post(f"/connections/{conn_id}/test")
            self.record("Connections", "Test valid connection", resp.status_code == 200, resp.text)

    async def phase_1_5_isolation(self):
        print("\n--- Phase 1.5: Multi-user Isolation ---")
        if "athletiq" not in self.connection_ids:
            self.record("Isolation", "User B accessing User A DB", False, "Skipped due to missing DB")
            return

        conn_id = self.connection_ids["athletiq"]
        
        # Try to test User A's connection using User B's client
        resp = await self.client2.post(f"/connections/{conn_id}/test")
        passed = resp.status_code == 404 or resp.status_code == 403
        self.record("Isolation", "User B blocked from User A connection", passed, f"Status: {resp.status_code}")

        # Try to fetch User A's connections with User B
        resp = await self.client2.get(f"/connections/{conn_id}")
        passed = resp.status_code == 404 or resp.status_code == 403
        self.record("Isolation", "User B blocked from GET User A connection", passed, f"Status: {resp.status_code}")

    async def phase_2_security(self):
        print("\n--- Phase 2: Security & Execution ---")
        if "athletiq" not in self.connection_ids:
            return

        conn_id = self.connection_ids["athletiq"]
        
        # 1. SQL Injection / Union based
        query = "SELECT * FROM users UNION ALL SELECT password FROM admin"
        resp = await self.client.post("/query/execute", json={
            "connection_id": conn_id,
            "query": query,
            "limit": 10
        })
        # Should be blocked
        passed = resp.status_code == 403 or (resp.status_code == 400 and "security" in resp.text.lower())
        self.record("Security", "Blocked UNION ALL Injection", passed, f"Status: {resp.status_code}")

        # 2. DROP TABLE
        query = "DROP TABLE users;"
        resp = await self.client.post("/query/execute", json={
            "connection_id": conn_id,
            "query": query,
            "limit": 10
        })
        passed = resp.status_code == 403 or (resp.status_code == 400 and "security" in resp.text.lower())
        self.record("Security", "Blocked DROP TABLE", passed, f"Status: {resp.status_code}")
        
    async def phase_3_5_concurrency(self):
        print("\n--- Phase 3.5: Concurrency ---")
        if "athletiq" not in self.connection_ids:
            return
            
        conn_id = self.connection_ids["athletiq"]
        query = "SELECT 1;"
        
        # Run 25 parallel queries
        tasks = []
        for i in range(25):
            tasks.append(self.client.post("/query/execute", json={"connection_id": conn_id, "query": query}))
            
        start_time = time.time()
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        
        successes = sum(1 for r in responses if isinstance(r, httpx.Response) and r.status_code == 200)
        passed = successes == 25
        self.record("Concurrency", "25 Parallel Queries", passed, f"{successes}/25 succeeded in {end_time - start_time:.2f}s")

    async def phase_5_schema_intelligence(self):
        print("\n--- Phase 5: Schema Intelligence ---")
        if "athletiq" not in self.connection_ids:
            return

        conn_id = self.connection_ids["athletiq"]
        
        # Fetch Schema
        resp = await self.client.get(f"/connections/{conn_id}/schema")
        passed = resp.status_code == 200
        self.record("Schema", "Fetch Schema Metadata", passed, f"Status: {resp.status_code}")

        # AI NL->SQL
        resp = await self.client.post("/ai/nl-to-sql", json={
            "connection_id": conn_id,
            "question": "Show me the top 5 users by creation date"
        })
        # Could fail if AI API key is not set, but the endpoint should exist
        passed = resp.status_code == 200
        self.record("AI", "NL -> SQL Generation", passed, f"Status: {resp.status_code}")


if __name__ == "__main__":
    verifier = ArgusVerifier()
    asyncio.run(verifier.run_all())
