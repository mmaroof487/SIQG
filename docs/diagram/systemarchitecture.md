```mermaid
graph TB
    subgraph CLIENT["Client Layer"]
        UI["React Frontend\n(Monaco + Recharts)"]
        SDK["Python SDK\n(pip install argus)"]
        CLI["CLI Tool\n(argus query)"]
    end

    subgraph GATEWAY["Argus Gateway (FastAPI)"]
        subgraph SEC["Security Layer"]
            TRACE["Trace ID\n(UUID4)"]
            AUTH["Auth\n(JWT / API Key)"]
            BF["Brute Force\n(Redis lockout)"]
            IP["IP Filter\n(allow/block)"]
            RL["Rate Limiter\n(sliding window)"]
            VAL["Validator\n(injection detect)"]
            RBAC["RBAC\n(role + columns)"]
            HON["Honeypot\n(fake tables)"]
        end

        subgraph PERF["Performance Layer"]
            FP["Fingerprinter\n(normalize + hash)"]
            CACHE["Cache Check\n(Redis GET)"]
            LIMIT["Auto-LIMIT\n(inject 1000)"]
            COST["Cost Estimator\n(EXPLAIN)"]
            BUDGET["Budget Check\n(daily quota)"]
        end

        subgraph EXEC["Execution Layer"]
            CB["Circuit Breaker\n(3 states)"]
            ENC["Encryptor\n(AES-256-GCM)"]
            ROUTER["Router\n(R/W split)"]
            POOL["Connection Pool\n(asyncpg)"]
            RUN["Execute + Timeout\n(retry backoff)"]
            EXPLAIN["EXPLAIN ANALYZE\n(post-exec)"]
            MASK["Decrypt + Mask\n(PII by role)"]
        end

        subgraph OBS["Observability Layer"]
            CWRITE["Cache Write\n(Redis SET)"]
            AUDIT["Audit Log\n(insert-only)"]
            METRICS["Metrics\n(Redis counters)"]
            WEBHOOK["Webhooks\n(Slack/Discord)"]
            HEAT["Heat Map\n(ZINCRBY)"]
        end

        subgraph AI["AI Layer"]
            NL["NL to SQL\n(LLM API)"]
            EXP["Query Explainer\n(LLM API)"]
        end
    end

    subgraph INFRA["Infrastructure"]
        PG_PRIMARY["PostgreSQL\nPrimary"]
        PG_REPLICA["PostgreSQL\nReplica"]
        REDIS["Redis\n(cache + sessions\n+ metrics + CB state)"]
    end

    subgraph EXTERNAL["External"]
        DISCORD["Discord / Slack\n(webhook alerts)"]
        OPENAI["OpenAI API\n(NL-to-SQL)"]
    end

    UI --> GATEWAY
    SDK --> GATEWAY
    CLI --> GATEWAY

    TRACE --> AUTH --> BF --> IP --> RL --> VAL --> RBAC --> HON
    HON --> FP --> CACHE
    CACHE -->|miss| LIMIT --> COST --> BUDGET --> CB
    CACHE -->|hit| MASK
    CB --> ENC --> ROUTER
    ROUTER -->|SELECT| PG_REPLICA
    ROUTER -->|INSERT/UPDATE| PG_PRIMARY
    ROUTER --> POOL --> RUN --> EXPLAIN --> MASK
    MASK --> CWRITE --> AUDIT --> METRICS --> WEBHOOK --> HEAT

    WEBHOOK --> DISCORD
    NL --> OPENAI
    EXP --> OPENAI

    CACHE -.-> REDIS
    CWRITE -.-> REDIS
    RL -.-> REDIS
    BF -.-> REDIS
    CB -.-> REDIS
    BUDGET -.-> REDIS
    METRICS -.-> REDIS
    HEAT -.-> REDIS
```