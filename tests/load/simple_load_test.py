#!/usr/bin/env python3
"""Simple load test script using urllib (no external dependencies)."""
import time
import statistics
import json
import urllib.request
import urllib.error
from urllib.parse import urlencode
from typing import List, Dict

BASE_URL = "http://localhost:8000"
API_URL = f"{BASE_URL}/api/v1"

class LoadTester:
    def __init__(self, num_users: int = 50, duration_seconds: int = 30):
        self.num_users = num_users
        self.duration = duration_seconds
        self.results: List[Dict] = []
        self.errors = 0
        self.start_time = None
        self.token = None
        
    def make_request(self, method: str, url: str, data: dict = None, headers: dict = None) -> tuple:
        """Make an HTTP request and measure latency."""
        start = time.time()
        try:
            if headers is None:
                headers = {}
            
            if data is not None:
                data = json.dumps(data).encode('utf-8')
                headers['Content-Type'] = 'application/json'
            
            req = urllib.request.Request(url, data=data, headers=headers, method=method)
            with urllib.request.urlopen(req, timeout=5) as response:
                latency = (time.time() - start) * 1000
                status = response.status
                return latency, status, None
        except urllib.error.HTTPError as e:
            latency = (time.time() - start) * 1000
            return latency, e.code, str(e)
        except Exception as e:
            latency = (time.time() - start) * 1000
            return latency, 0, str(e)
    
    def setup_auth(self):
        """Register and get auth token (simplified)."""
        try:
            # For simplicity, we'll use a basic token
            # In real scenario, this would register/login
            timestamp = int(time.time())
            latency, status, error = self.make_request(
                "POST",
                f"{API_URL}/auth/register",
                {
                    "username": f"loadtest_user_{timestamp}",
                    "email": f"loadtest_{timestamp}@test.com",
                    "password": "LoadTest@1234"
                }
            )
            # For this demo, we'll continue without token verification
            return True
        except Exception as e:
            print(f"Auth setup: {e}")
        return False
    
    def run_single_request(self, query_type: str) -> Dict:
        """Run a single request and measure latency."""
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        
        try:
            if query_type == "health":
                latency, status, error = self.make_request("GET", f"{BASE_URL}/health", headers=headers)
            elif query_type == "metrics":
                latency, status, error = self.make_request("GET", f"{API_URL}/metrics/live", headers=headers)
            elif query_type == "simple_query":
                latency, status, error = self.make_request(
                    "POST",
                    f"{API_URL}/query/execute",
                    {"query": "SELECT 1 AS test"},
                    headers
                )
            elif query_type == "complex_query":
                latency, status, error = self.make_request(
                    "POST",
                    f"{API_URL}/query/execute",
                    {"query": "SELECT * FROM pg_database LIMIT 10"},
                    headers
                )
            elif query_type == "dry_run":
                latency, status, error = self.make_request(
                    "POST",
                    f"{API_URL}/query/execute",
                    {"query": "SELECT * FROM pg_tables", "dry_run": True},
                    headers
                )
            else:
                return None
            
            success = status < 400 and error is None
            if not success:
                self.errors += 1
            
            return {
                "type": query_type,
                "latency_ms": latency,
                "status_code": status,
                "success": success
            }
        except Exception as e:
            self.errors += 1
            return {
                "type": query_type,
                "latency_ms": 0,
                "status_code": 0,
                "success": False,
                "error": str(e)
            }
    
    def simulate_concurrent_load(self):
        """Simulate concurrent users making requests."""
        print(f"Starting load test: ~{self.num_users} sequential requests, {self.duration}s target")
        print(f"Target: {BASE_URL}")
        print()
        
        # Set up auth (skip token verification for simplicity)
        self.setup_auth()
        
        requests_made = 0
        self.start_time = time.time()
        request_types = ["health", "metrics", "simple_query", "complex_query", "dry_run"]
        type_index = 0
        
        while time.time() - self.start_time < self.duration:
            # Cycle through different request types
            query_type = request_types[type_index % len(request_types)]
            type_index += 1
            
            result = self.run_single_request(query_type)
            if result:
                self.results.append(result)
                requests_made += 1
                
                # Print progress
                if requests_made % 10 == 0:
                    elapsed = time.time() - self.start_time
                    rate = requests_made / elapsed if elapsed > 0 else 0
                    print(f"[{elapsed:.1f}s] Made {requests_made} requests ({rate:.1f} req/s)")
        
        return requests_made
    
    def print_results(self):
        """Print summary statistics."""
        if not self.results:
            print("No results to report!")
            return
        
        elapsed = time.time() - self.start_time
        latencies = [r["latency_ms"] for r in self.results if r["success"]]
        unsuccessful = len([r for r in self.results if not r["success"]])
        
        print("\n" + "="*60)
        print("LOAD TEST RESULTS")
        print("="*60)
        print(f"Total Requests: {len(self.results)}")
        print(f"Successful: {len(latencies)}")
        print(f"Failed: {unsuccessful}")
        print(f"Errors: {self.errors}")
        print(f"Duration: {elapsed:.1f}s")
        print(f"Request Rate: {len(self.results)/elapsed:.1f} req/s")
        print()
        
        if latencies:
            print("LATENCY STATISTICS (ms)")
            print("-" * 60)
            print(f"Min: {min(latencies):.2f}ms")
            print(f"Max: {max(latencies):.2f}ms")
            print(f"Mean: {statistics.mean(latencies):.2f}ms")
            print(f"Median: {statistics.median(latencies):.2f}ms")
            if len(latencies) > 1:
                p95_idx = int(len(latencies)*0.95)
                p99_idx = int(len(latencies)*0.99)
                if p95_idx < len(latencies):
                    print(f"P95: {sorted(latencies)[p95_idx]:.2f}ms")
                if p99_idx < len(latencies):
                    print(f"P99: {sorted(latencies)[p99_idx]:.2f}ms")
                print(f"StdDev: {statistics.stdev(latencies):.2f}ms")
            print()
        
        # Breakdown by request type
        print("BREAKDOWN BY REQUEST TYPE")
        print("-" * 60)
        by_type = {}
        for result in self.results:
            req_type = result["type"]
            if req_type not in by_type:
                by_type[req_type] = []
            if result["success"]:
                by_type[req_type].append(result["latency_ms"])
        
        for req_type in sorted(by_type.keys()):
            lats = by_type[req_type]
            if lats:
                p95 = sorted(lats)[int(len(lats)*0.95)] if len(lats) > 1 else lats[0]
                print(f"{req_type:20s}: {len(lats):4d} requests, avg: {statistics.mean(lats):7.2f}ms, p95: {p95:.2f}ms")
        
        print()
        if len(self.results) > 0:
            print(f"Success Rate: {len(latencies)/len(self.results)*100:.1f}%")
        print("="*60)
        print()

if __name__ == "__main__":
    # Run load test with 50 concurrent users for 30 seconds
    tester = LoadTester(num_users=50, duration_seconds=30)
    tester.simulate_concurrent_load()
    tester.print_results()
