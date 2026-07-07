# Argus Encryption Subsystem Guide

Argus provides transparent, column-level AES-256-GCM encryption for connected databases.

## Architecture

```mermaid
sequenceDiagram
    participant App as Application
    participant Argus as Argus Gateway
    participant KMS as KeyManager (Vault/Local)
    participant DB as Target PostgreSQL

    App->>Argus: INSERT INTO users (email) VALUES ('test@example.com')
    Argus->>KMS: Retrieve active Data Encryption Key (DEK)
    KMS-->>Argus: Return DEK + Key ID
    Argus->>Argus: Encrypt 'test@example.com' with DEK
    Argus->>DB: INSERT INTO users (email) VALUES ('v1:enc_data_here')
    DB-->>Argus: OK
    Argus-->>App: Success
```

## Key Rotation
Argus supports live key rotation. When a new key is provisioned:
1. The new key becomes the **Active Key** for all new writes.
2. The old key is retained as an **Archive Key** to decrypt existing data.
3. The background **Migration Worker** scans encrypted columns and re-encrypts old data with the new active key in batches.

## Usage
Encryption rules are applied to specific columns via the API:
`POST /api/v1/connections/{id}/encryption`
```json
{
  "schema_name": "public",
  "table_name": "users",
  "column_name": "email",
  "classification_method": 3,
  "is_encrypted": true
}
```

Argus will automatically intercept queries reading or writing to `public.users.email` and handle cryptographic operations transparently.
