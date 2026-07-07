# Argus v1.0 Release Notes

**Date:** July 2026

We are incredibly proud to announce the **v1.0 General Availability** release of **Argus - Secure Intelligent Query Gateway**. 

Argus has evolved from an academic proof-of-concept into a production-ready, highly secure middleware for modern database environments.

## Major Features in v1.0

### 1. Robust Security & Encryption
- **AES-256-GCM Column-Level Encryption**: Fully transparent to the application. Data is encrypted in transit and at rest in the external database.
- **Key Rotation & Migration**: Background workers seamlessly migrate data to new encryption keys without downtime.
- **Advanced RBAC & Time-Based Access**: Restrict queries by role, table, column, and even time-of-day.
- **Query Whitelisting**: Lock down critical databases to only allow specific query fingerprints.

### 2. DevOps & Observability
- **OpenTelemetry & Prometheus**: Full support for distributed tracing (trace_id injected into logs) and metrics scraping (`/metrics`).
- **Structured JSON Logging**: Centralized, machine-readable logs for SIEM ingestion.
- **Readiness & Liveness Probes**: Kubernetes-native health endpoints (`/health/live`, `/health/ready`).

### 3. High Performance
- **Semantic Caching**: Intelligent query caching powered by Redis, drastically reducing load on primary databases.
- **Connection Pooling**: Optimized asyncpg connection lifecycle management.

### 4. Admin Tooling
- Included out-of-the-box bootstrapping (`scripts/bootstrap_admin.py`).
- Integrated backup and restore scripts for configuration state.

## Upgrade Path
Argus v1.0 introduces a formal migration system for database connections. No breaking changes exist for the core `/query/execute` endpoint.

## Security Posture
We successfully integrated automated SAST (Semgrep) and dependency scanning (Trivy) into our GitHub Actions pipelines.

## Acknowledgements
Thank you to the community and early adopters who helped test Argus across millions of queries to ensure rock-solid stability!
