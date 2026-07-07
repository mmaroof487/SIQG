# Argus SDK Guide (Python)

The Argus Python SDK provides a convenient wrapper around the Argus REST API.

## Installation
```bash
pip install argus-sdk
```

## Quick Start

```python
from argus import ArgusClient

# Initialize client
client = ArgusClient(
    base_url="http://localhost:8000/api/v1",
    api_key="your_jwt_token"
)

# Execute a query
result = client.query(
    connection_id="123e4567-e89b-12d3-a456-426614174000",
    sql="SELECT username, email FROM users",
    limit=10
)

print(f"Found {result.rows_count} rows in {result.execution_time_ms}ms")
print(result.data)

# Use AI capabilities
sql = client.nl_to_sql(
    connection_id="123e4567-e89b-12d3-a456-426614174000",
    question="Count the number of active users"
)
print("Generated SQL:", sql)
```

## Error Handling
The SDK handles circuit breaker and rate limit responses transparently, throwing strongly-typed exceptions:
- `ArgusRateLimitExceeded`
- `ArgusCircuitBreakerOpen`
- `ArgusQueryTimeout`
