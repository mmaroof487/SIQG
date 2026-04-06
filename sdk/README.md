# Argus SDK

Python SDK for **Argus** - Secure Intelligent Query Gateway

## Features

- 🔐 **Secure**: JWT authentication, rate limiting, SQL injection prevention
- ⚡ **Fast**: Query caching, cost estimation, performance monitoring
- 🤖 **Intelligent**: NL→SQL conversion, query explanation
- 📊 **Observable**: Trace IDs, audit logs, metrics, alerting

## Installation

```bash
pip install -e .
```

Or from PyPI (when published):

```bash
pip install argus-sdk
```

## Quick Start

### Python Library

```python
from argus import Gateway

# Initialize and login
gw = Gateway("http://localhost:8000").login("admin", "password")

# Execute a query
result = gw.query("SELECT * FROM users LIMIT 10")
print(f"Got {result['rows_count']} rows in {result['latency_ms']:.1f}ms")

# Explain a query
explanation = gw.explain("SELECT COUNT(*) FROM orders")
print(explanation)

# Convert natural language to SQL
result = gw.nl_to_sql("How many users signed up in the last 7 days?")
print(result["generated_sql"])
print(result["result"]["rows"])

# Dry-run mode (validate and estimate cost, no execution)
result = gw.query("SELECT * FROM users", dry_run=True)
print(result["analysis"]["pipeline_checks"])

# Check gateway status
status = gw.status()
print(f"Gateway: {status['status']}, DB: {status['db']}, Redis: {status['redis']}")

# Get metrics
metrics = gw.metrics()
print(f"Cache hit rate: {metrics['cache_hit_rate']:.1%}")
```

### CLI Tool

```bash
# Login and save credentials
argus login http://localhost:8000 admin password

# Execute a query
argus query "SELECT * FROM users LIMIT 10"

# Dry-run mode
argus query "SELECT * FROM users" --dry-run

# Explain a query
argus explain "SELECT COUNT(*) FROM orders WHERE status = 'pending'"

# Convert natural language to SQL
argus nl-to-sql "How many users signed up in the last 7 days?"

# Check status
argus status

# Logout
argus logout
```

## Authentication

The SDK supports two authentication methods:

```python
# API Key
gw = Gateway("http://localhost:8000", api_key="your-api-key")

# JWT Token (from login or saved)
gw = Gateway("http://localhost:8000", jwt_token="your-jwt-token")
```

The CLI automatically saves your login token to `~/.argus_token` for convenience.

## Query Response Format

```python
result = gw.query("SELECT * FROM users LIMIT 10")

# Response structure:
{
    "trace_id": "uuid",
    "query_type": "SELECT",
    "rows": [...],
    "rows_count": 10,
    "latency_ms": 45.3,
    "cached": False,
    "cost": 100.5,
    "analysis": {
        "scan_type": "Index Scan",
        "execution_time_ms": 40.2,
        "total_cost": 100.5,
        "complexity": "LOW",
        "index_suggestions": []
    }
}
```

## Dry-Run Mode

Validate queries and estimate costs without executing:

```python
result = gw.query("SELECT * FROM users", dry_run=True)

# Dry-run response includes pipeline checks
print(result["analysis"]["pipeline_checks"])
# {
#     "ip_filter": "pass",
#     "rate_limit": "pass",
#     "injection_check": "pass",
#     "rbac": "pass",
#     "honeypot": "pass"
# }
```

## Error Handling

```python
from argus import Gateway
import httpx

try:
    gw = Gateway("http://localhost:8000").login("admin", "wrong-password")
except httpx.HTTPError as e:
    print(f"Authentication failed: {e}")

# Explicit task error handling:
result = gw.nl_to_sql("SELECT * FROM users")
if result["status"] == "error":
    print(f"NL→SQL failed: {result['message']}")
```

## Live Demo

### Interactive CLI Demo

See the SDK in action with a complete user journey:

```bash
# Start the backend (if not already running)
docker compose up --build

# In another terminal, run the demo
bash demo_cli.sh
```

**Demo includes:**

- ✓ User registration and authentication
- ✓ SQL query execution with latency tracking
- ✓ Natural language to SQL conversion
- ✓ Query explanation in plain English
- ✓ Dry-run mode for cost estimation
- ✓ System health checks
- ✓ Live performance metrics

**Expected output:** See [DEMO_OUTPUT.md](../DEMO_OUTPUT.md) for sample results

### Web Dashboard Demo

For a visual demo, the web dashboard is available at:

```
http://localhost:3000
```

Includes:

- Query page with NL input and results
- Live metrics dashboard (latency, cache hit rates)
- System health status page

## Development

### Running Tests

```bash
cd ..
python -m pytest tests/unit/test_sdk_client.py -v
```

### Building the Package

```bash
python setup.py sdist bdist_wheel
```

## License

MIT

## Support

For issues and feature requests, visit: https://github.com/mmaroof487/SIQG
