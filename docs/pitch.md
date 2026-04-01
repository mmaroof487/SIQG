I built a system called **Argus**, which is essentially a middleware layer that sits between an application and a PostgreSQL database. The idea came from a common issue I noticed — most applications send queries directly to the database with very little control or visibility over what’s actually being executed.

That creates a few real problems in production: things like SQL injection risks, poorly written queries affecting performance, and almost no visibility into who accessed what data or why. Argus solves this by acting as a controlled gateway where every query is intercepted and processed before it reaches the database.

The system is designed as a layered pipeline. First, there’s a security layer that handles authentication, rate limiting, SQL injection detection, and role-based access control. Then comes the performance layer, where queries are fingerprinted and cached using Redis, and I also estimate query cost before execution and enforce limits to prevent heavy queries.

The execution layer focuses on reliability — I implemented a circuit breaker with open, half-open, and closed states, along with retry logic using exponential backoff. There’s also read/write routing between primary and replica databases, and column-level encryption for sensitive fields.

On top of that, I built an intelligence layer that runs EXPLAIN ANALYZE on queries and extracts useful insights like execution time, scan type, and even generates index recommendations automatically. Then there’s an observability layer where every request is logged with trace IDs, metrics are tracked in Redis, and slow queries or anomalies trigger alerts.

In the final phase, I added an AI layer where users can write queries in natural language and have them converted to SQL, and also get plain English explanations of existing queries. One important design choice here was that even AI-generated queries are not trusted directly — they go through the same validation and execution pipeline as everything else.

To make the system usable beyond just APIs, I built a Python SDK and a CLI tool, so you can interact with Argus programmatically or from the terminal. The whole system runs using Docker with PostgreSQL, Redis, and the gateway as separate services.

I also focused a lot on validation — the system is covered by 130+ tests across unit, integration, and AI components, and I verified it manually using end-to-end flows through the CLI.

Overall, the goal wasn’t just to build features, but to design something that behaves like a real backend system — where security, performance, reliability, and observability are all handled in a single controlled layer.
