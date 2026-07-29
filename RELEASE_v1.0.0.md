# Argus v1.0.0 🚀

We are incredibly excited to announce the first production release of **Argus**! 

Argus is a production-ready AI-powered SQL gateway built to sit transparently between your applications and PostgreSQL. It brings zero-trust security, intelligent caching, LLM integration, and envelope encryption to any database without modifying your application code.

## ✨ Highlights

* **Multi-database gateway**: Connect and proxy multiple PostgreSQL instances through a single centralized gateway.
* **AI SQL generation**: Translate natural language directly into secure, deterministic SQL using Groq LLMs.
* **Redis caching**: Role-aware, query-fingerprinted caching that serves repeated queries in under 5ms and invalidates via table-tagging.
* **Envelope encryption**: Two-tier (KEK/DEK) AES-256-GCM encryption with live key rotation and background decryption migrations.
* **Schema intelligence**: Explores relationships, builds BFS adjacency graphs, and provides a rich UI for schema visualization.
* **React dashboard**: A beautiful, modern TypeScript/Vite frontend featuring a Query Studio, Schema Explorer, and Security Center.
* **Observability**: Rich telemetry tracking execution times, cache hit ratios, and a fire-and-forget asynchronous audit log for SOC2 compliance.

## 🛡️ Security & Reliability

This release marks the completion of our production readiness initiatives:
* **AST Validation**: Deep parsing of SQL ensures no `DROP`, `TRUNCATE`, or `ALTER` statements can sneak past the gateway.
* **Honeypot Traps**: Immediate IP bans for unauthorized access to decoy tables.
* **RBAC & Data Masking**: Dynamic column masking (e.g. `***@***.com`) and isolation between admin and readonly users.
* **Automated Testing**: Passing integration, E2E, and locust stress tests under heavy concurrency.
* **CI/CD Integration**: Zero High/Critical vulnerabilities via strict `pip-audit` and `npm audit` enforcement.

## 📝 Known Limitations
* SQL edge cases (allow/block matrix) parser testing is partially covered and will be expanded in v1.0.1.

## 📦 What's Next?
* See our [Documentation](docs/ARCHITECTURE.md) to get started with deployment.
* Stay tuned for Automated Cache Warming and SQLite support in v1.1!

---
*Built with precision. Enjoy Argus v1.0!*
