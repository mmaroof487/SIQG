"""Argus SDK - Python client for the Secure Intelligent Query Gateway.

This SDK provides a simple interface to interact with the Argus gateway,
supporting query execution, natural language to SQL conversion, query explanation,
and status checks.

Example:
    from argus import Gateway

    # Login and execute a query
    gw = Gateway("http://localhost:8000").login("admin", "password")
    result = gw.query("SELECT * FROM users LIMIT 10")
    print(result["rows"])

    # Explain a query
    explanation = gw.explain("SELECT COUNT(*) FROM orders")
    print(explanation)

    # Convert natural language to SQL
    result = gw.nl_to_sql("How many users signed up in the last 7 days?")
    print(result["generated_sql"])

    # Dry-run mode
    result = gw.query("SELECT * FROM users", dry_run=True)
    print(result["analysis"]["pipeline_checks"])
"""
import httpx
from typing import Optional, Dict, List, Any
import json
from pathlib import Path


class Gateway:
    """Argus gateway client for executing queries and interacting with AI features."""

    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        jwt_token: Optional[str] = None,
    ):
        """
        Initialize Argus gateway client.

        Args:
            base_url: Gateway base URL (e.g., "http://localhost:8000")
            api_key: Optional API key for authentication
            jwt_token: Optional JWT token for authentication

        Example:
            gw = Gateway("http://localhost:8000", api_key="your-api-key")
        """
        self.base_url = base_url.rstrip("/")
        self._headers = {"Content-Type": "application/json"}
        self.session = None

        if api_key:
            self._headers["X-API-Key"] = api_key
        if jwt_token:
            self._headers["Authorization"] = f"Bearer {jwt_token}"

    def login(self, username: str, password: str) -> "Gateway":
        """
        Log in to the gateway and obtain JWT token.

        Args:
            username: Username
            password: Password

        Returns:
            Self for method chaining

        Raises:
            httpx.HTTPError: If login fails
        """
        with httpx.Client() as client:
            resp = client.post(
                f"{self.base_url}/api/v1/auth/login",
                headers={"Content-Type": "application/json"},
                json={"username": username, "password": password},
                timeout=10.0,
            )
            resp.raise_for_status()
            data = resp.json()
            token = data.get("access_token")
            if not token:
                raise ValueError("No access token in login response")
            self._headers["Authorization"] = f"Bearer {token}"
        return self

    def query(
        self,
        sql: str,
        encrypt_columns: Optional[List[str]] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Execute a SQL query through the Argus gateway.

        Args:
            sql: SQL query string
            encrypt_columns: Optional list of columns to encrypt
            dry_run: If True, validate and estimate cost without executing

        Returns:
            Dict containing:
                - trace_id: Request trace ID
                - query_type: SELECT or INSERT
                - rows: Result rows
                - rows_count: Number of rows
                - latency_ms: Execution time
                - cached: Whether result was cached
                - cost: Estimated cost
                - analysis: Query analysis details

        Example:
            result = gw.query("SELECT * FROM users LIMIT 10")
            print(f"Got {result['rows_count']} rows in {result['latency_ms']:.1f}ms")
        """
        with httpx.Client() as client:
            resp = client.post(
                f"{self.base_url}/api/v1/query/execute",
                headers=self._headers,
                json={
                    "query": sql,
                    "encrypt_columns": encrypt_columns or [],
                    "dry_run": dry_run,
                },
                timeout=30.0,
            )
            resp.raise_for_status()
            return resp.json()

    def explain(self, sql: str) -> str:
        """
        Get a plain English explanation of a SQL query.

        Args:
            sql: SQL query string

        Returns:
            Plain English explanation of the query

        Example:
            explanation = gw.explain("SELECT COUNT(*) FROM orders WHERE status = 'pending'")
            print(explanation)
        """
        with httpx.Client() as client:
            resp = client.post(
                f"{self.base_url}/api/v1/ai/explain",
                headers=self._headers,
                json={"query": sql},
                timeout=10.0,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("explanation", "")

    def nl_to_sql(
        self, question: str, schema_hint: str = ""
    ) -> Dict[str, Any]:
        """
        Convert a natural language question to SQL and execute it.

        Args:
            question: Natural language question
            schema_hint: Optional schema hint (e.g., "table users(id, name, email)")

        Returns:
            Dict containing:
                - original_question: The input question
                - generated_sql: The generated SQL query
                - result: Query result from execution
                - status: "success" or "error"
                - message: Error message if status is "error"

        Example:
            result = gw.nl_to_sql("How many users signed up in the last 7 days?")
            if result["status"] == "success":
                print(f"Generated SQL: {result['generated_sql']}")
                print(f"Result: {result['result']['rows']}")
        """
        with httpx.Client() as client:
            resp = client.post(
                f"{self.base_url}/api/v1/ai/nl-to-sql",
                headers=self._headers,
                json={
                    "question": question,
                    "schema_hint": schema_hint,
                },
                timeout=15.0,
            )
            resp.raise_for_status()
            return resp.json()

    def status(self) -> Dict[str, str]:
        """
        Check gateway health and status.

        Returns:
            Dict with status fields (status, db, redis)

        Example:
            status = gw.status()
            print(f"Gateway: {status['status']}, DB: {status['db']}, Redis: {status['redis']}")
        """
        with httpx.Client() as client:
            resp = client.get(f"{self.base_url}/health", timeout=5.0)
            resp.raise_for_status()
            return resp.json()

    def metrics(self) -> Dict[str, Any]:
        """
        Get current gateway metrics.

        Returns:
            Dict containing various metrics (latency, cache hit rate, etc.)
        """
        with httpx.Client() as client:
            resp = client.get(
                f"{self.base_url}/api/v1/metrics/live",
                headers=self._headers,
                timeout=5.0,
            )
            resp.raise_for_status()
            return resp.json()
