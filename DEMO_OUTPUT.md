═══════════════════════════════════════════════════════════════
   Argus SDK CLI Demo — Complete User Journey
═══════════════════════════════════════════════════════════════

📝 Step 1: Registering new user...
✓ User registered (or already exists)

🔐 Step 2: Logging in and retrieving access token...
✓ Access token retrieved: eyJhbGciOiJIUzI1NiIs...

⚡ Step 3: Executing a SQL query (cached)...
   Query: SELECT id, username FROM users LIMIT 5
✓ Query executed in 3.42ms, returned 5 rows

🤖 Step 4: Converting natural language to SQL...
   Question: 'Top 5 users created this month'
✓ Generated SQL:
   SELECT id, username, email, created_at FROM users 
   WHERE created_at >= DATE_TRUNC('month', NOW()) 
   ORDER BY created_at DESC LIMIT 5

📖 Step 5: Explaining a complex query...
✓ Explanation: This query counts the number of unique active users per day 
   over the last 7 days by analyzing the audit log, grouping by date 
   and sorting in descending order.

🔍 Step 6: Running in dry-run mode (no DB execution)...
✓ Estimated cost: 145 units (query was NOT executed)

📊 Step 7: Checking gateway health and status...
✓ Gateway Status:
   {
     "status": "healthy",
     "database": {
       "primary": "connected",
       "replica": "connected"
     },
     "cache": "ready",
     "circuit_breaker": "closed",
     "uptime_seconds": 3847
   }

📈 Step 8: Viewing live performance metrics...
✓ Cache hit rate: 68.5%
✓ P95 latency: 12.3ms

═══════════════════════════════════════════════════════════════
   ✅ Demo Complete!
═══════════════════════════════════════════════════════════════

Features Demonstrated:
  ✓ Authentication (register, login, token)
  ✓ Query execution with latency tracking
  ✓ Natural language to SQL conversion
  ✓ Query explanation in plain English
  ✓ Dry-run mode for cost estimation
  ✓ Health checks
  ✓ Live performance metrics

Next Steps:
  → Open http://localhost:3000 for the web dashboard
  → Run 'bash test_userguide_sequential.sh' for full test suite
  → Check SDK/CLI docs: sdk/README.md
