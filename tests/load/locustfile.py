"""Load tests using Locust — covers all 4 layers."""
from locust import HttpUser, task, between


class ArgusUser(HttpUser):
    wait_time = between(0.5, 2)

    def on_start(self):
        """Register and login to get auth token."""
        import uuid
        self.username = f"loadtest_{uuid.uuid4().hex[:8]}"
        # Try to register
        reg = self.client.post(
            "/api/v1/auth/register",
            json={
                "username": self.username,
                "email": f"{self.username}@test.com",
                "password": "LoadTest@1234",
            },
        )
        if reg.status_code == 200:
            self.token = reg.json().get("access_token", "")
        else:
            # Fallback: try login
            login = self.client.post(
                "/api/v1/auth/login",
                json={
                    "username": self.username,
                    "password": "LoadTest@1234",
                },
            )
            self.token = login.json().get("access_token", "") if login.status_code == 200 else ""
        self.headers = {"Authorization": f"Bearer {self.token}"}

    @task(3)
    def health_check(self):
        """Layer 4: Health endpoint (unauthenticated)."""
        self.client.get("/health")

    @task(2)
    def live_metrics(self):
        """Layer 4: Live metrics endpoint (unauthenticated)."""
        self.client.get("/api/v1/metrics/live")

    @task(5)
    def select_query(self):
        """Layer 1-4: Full pipeline SELECT (cache miss → hit cycle)."""
        self.client.post(
            "/api/v1/query/execute",
            json={"query": "SELECT 1 AS load_test"},
            headers=self.headers,
        )

    @task(3)
    def select_with_where(self):
        """Layer 2: Query fingerprinting + cache differentiation."""
        self.client.post(
            "/api/v1/query/execute",
            json={"query": "SELECT * FROM pg_database WHERE datname = 'postgres'"},
            headers=self.headers,
        )

    @task(1)
    def dry_run(self):
        """Layer 2: Cost estimation without execution."""
        self.client.post(
            "/api/v1/query/execute",
            json={"query": "SELECT * FROM pg_tables", "dry_run": True},
            headers=self.headers,
        )

    @task(1)
    def check_budget(self):
        """Layer 2: Budget status endpoint."""
        self.client.get(
            "/api/v1/query/budget",
            headers=self.headers,
        )

    @task(1)
    def blocked_injection(self):
        """Layer 1: SQL injection should return 400."""
        with self.client.post(
            "/api/v1/query/execute",
            json={"query": "SELECT * FROM users WHERE id=1 OR 1=1"},
            headers=self.headers,
            catch_response=True,
        ) as response:
            if response.status_code == 400:
                response.success()  # Expected behavior

    @task(1)
    def blocked_drop(self):
        """Layer 1: DROP TABLE should return 400."""
        with self.client.post(
            "/api/v1/query/execute",
            json={"query": "DROP TABLE users"},
            headers=self.headers,
            catch_response=True,
        ) as response:
            if response.status_code == 400:
                response.success()
