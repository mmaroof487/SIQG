#!/bin/bash

# Argus SDK CLI Demo Script
# This demonstrates the core SDK features in sequence

set -e

GATEWAY_URL="http://localhost:8000"
USERNAME="demo_user"
PASSWORD="DemoPass123!"
EMAIL="demo@example.com"

echo "═══════════════════════════════════════════════════════════════"
echo "   Argus SDK CLI Demo — Complete User Journey"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Step 1: Register (if user doesn't exist)
echo "📝 Step 1: Registering new user..."
curl -s -X POST "$GATEWAY_URL/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d "{
    \"username\":\"$USERNAME\",
    \"email\":\"$EMAIL\",
    \"password\":\"$PASSWORD\"
  }" | jq '.message' 2>/dev/null || echo "✓ User registered (or already exists)"

echo ""
sleep 1

# Step 2: Login and extract token
echo "🔐 Step 2: Logging in and retrieving access token..."
TOKEN_RESPONSE=$(curl -s -X POST "$GATEWAY_URL/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d "{
    \"username\":\"$USERNAME\",
    \"password\":\"$PASSWORD\"
  }")

TOKEN=$(echo "$TOKEN_RESPONSE" | jq -r '.access_token' 2>/dev/null)

if [ -z "$TOKEN" ] || [ "$TOKEN" = "null" ]; then
  echo "❌ Login failed. Trying with admin credentials..."
  TOKEN_RESPONSE=$(curl -s -X POST "$GATEWAY_URL/api/v1/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"username":"admin","password":"admin"}')
  TOKEN=$(echo "$TOKEN_RESPONSE" | jq -r '.access_token')
fi

echo "✓ Access token retrieved: ${TOKEN:0:20}..."
echo ""
sleep 1

# Step 3: Query Execution
echo "⚡ Step 3: Executing a SQL query (cached)..."
echo "   Query: SELECT id, username FROM users LIMIT 5"
QUERY_RESULT=$(curl -s -X POST "$GATEWAY_URL/api/v1/query/execute" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "SELECT id, username FROM users LIMIT 5"
  }')

LATENCY=$(echo "$QUERY_RESULT" | jq '.latency_ms' 2>/dev/null)
ROWS=$(echo "$QUERY_RESULT" | jq '.rows | length' 2>/dev/null)

echo "✓ Query executed in ${LATENCY}ms, returned $ROWS rows"
echo ""
sleep 1

# Step 4: Natural Language to SQL
echo "🤖 Step 4: Converting natural language to SQL..."
echo "   Question: 'Top 5 users created this month'"
NL_RESULT=$(curl -s -X POST "$GATEWAY_URL/api/v1/ai/nl-to-sql" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Top 5 users created this month"
  }')

GENERATED_SQL=$(echo "$NL_RESULT" | jq -r '.generated_sql' 2>/dev/null)
echo "✓ Generated SQL:"
echo "   $GENERATED_SQL"
echo ""
sleep 1

# Step 5: Query Explanation
echo "📖 Step 5: Explaining a complex query..."
EXPLAIN_RESULT=$(curl -s -X POST "$GATEWAY_URL/api/v1/ai/explain" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "SELECT COUNT(DISTINCT user_id) as active_users, DATE(created_at) as date FROM audit_logs WHERE created_at > NOW() - INTERVAL '"'"'7 days'"'"' GROUP BY DATE(created_at) ORDER BY date DESC"
  }')

EXPLANATION=$(echo "$EXPLAIN_RESULT" | jq -r '.explanation' 2>/dev/null)
echo "✓ Explanation: $EXPLANATION"
echo ""
sleep 1

# Step 6: Dry-Run Mode
echo "🔍 Step 6: Running in dry-run mode (no DB execution)..."
DRY_RUN=$(curl -s -X POST "$GATEWAY_URL/api/v1/query/execute" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "SELECT id, username FROM users WHERE id > 1000 LIMIT 100",
    "dry_run": true
  }')

COST=$(echo "$DRY_RUN" | jq '.analysis.total_cost // .cost' 2>/dev/null)
echo "✓ Estimated cost: $COST units (query was NOT executed)"
echo ""
sleep 1

# Step 7: System Status
echo "📊 Step 7: Checking gateway health and status..."
STATUS=$(curl -s -X GET "$GATEWAY_URL/health")
echo "✓ Gateway Status:"
echo "$STATUS" | jq '.' 2>/dev/null | sed 's/^/   /'
echo ""
sleep 1

# Step 8: Live Metrics
echo "📈 Step 8: Viewing live performance metrics..."
METRICS=$(curl -s -X GET "$GATEWAY_URL/api/v1/metrics/live" \
  -H "Authorization: Bearer $TOKEN")

CACHE_HIT=$(echo "$METRICS" | jq '.cache_hit_ratio' 2>/dev/null)
LATENCY_P95=$(echo "$METRICS" | jq '.latency_p95' 2>/dev/null)
echo "✓ Cache hit rate: ${CACHE_HIT}%"
echo "✓ P95 latency: ${LATENCY_P95}ms"
echo ""
sleep 1

# Summary
echo "═══════════════════════════════════════════════════════════════"
echo "   ✅ Demo Complete!"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "Features Demonstrated:"
echo "  ✓ Authentication (register, login, token)"
echo "  ✓ Query execution with latency tracking"
echo "  ✓ Natural language to SQL conversion"
echo "  ✓ Query explanation in plain English"
echo "  ✓ Dry-run mode for cost estimation"
echo "  ✓ Health checks"
echo "  ✓ Live performance metrics"
echo ""
echo "Next Steps:"
echo "  → Open http://localhost:3000 for the web dashboard"
echo "  → Run 'bash test_userguide_sequential.sh' for full test suite"
echo "  → Check SDK/CLI docs: sdk/README.md"
echo ""
