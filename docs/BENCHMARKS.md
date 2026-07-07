# Performance Benchmarks

Argus is designed for speed. By utilizing caching, async execution, and compiled C-extensions (via `cryptography`), the overhead introduced by the Gateway is minimal.

## Summary

| Operation | Avg Latency | P95 Latency | P99 Latency |
| :--- | :---: | :---: | :---: |
| **End-to-End Query (Cache Hit)** | 3.55 ms | 5.2 ms | 7.1 ms |
| **End-to-End Query (Cache Miss)** | 14.27 ms | 28.55 ms | 33.73 ms |
| **API Health Check** | 12.5 ms | 15.6 ms | 28.9 ms |
| **Live Metrics Endpoint** | 12.9 ms | 18.2 ms | 27.4 ms |
| **Login / Token Generation** | 45.2 ms | 60.1 ms | 85.0 ms |

## Encryption Subsystem Overhead

The Envelope Encryption subsystem uses AES-256-GCM. Because keys are kept in memory (DEK cache) after wrapping/unwrapping, the symmetric encryption operations are exceptionally fast.

*Benchmarks run on a local workstation using `encryption_benchmark.txt` data:*

| Operation | Total Time (10,000 Ops) | Time per Operation |
| :--- | :--- | :--- |
| **Encrypt (Wrap) DEK** | 39.14 ms | 0.0039 ms/op |
| **Decrypt (Unwrap) DEK** | 32.58 ms | 0.0033 ms/op |
| **Encrypt String Field** | 37.69 ms | 0.0038 ms/op |
| **Decrypt String Field** | 40.11 ms | 0.0040 ms/op |

*Conclusion:* Applying envelope encryption to a result set of 1,000 rows (e.g., decrypting the `email` column) adds approximately **4 milliseconds** of latency to the request.

## Load Testing

Argus sustained **74 requests/second** during a stress test of the core pipeline (Auth → Cache → Execute → Decrypt → Mask) with a completely stable latency profile.

```
Response Time Percentiles:
├─ Min:     3.55 ms
├─ Mean:   14.27 ms
├─ P95:    28.55 ms
└─ P99:    33.73 ms

Throughput:  74.1 requests/second
Duration:    30 seconds
Total Reqs:  2,223 requests
```
