"""Load tests using Locust."""
from locust import HttpUser, task, between


class QueryxUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def health_check(self):
        self.client.get("/health")

    @task
    def check_status(self):
        self.client.get("/api/v1/status")
