"""Gateway configuration using pydantic-settings (Pydantic v2+)."""
from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import List
import os
from utils.logger import get_logger

logger = get_logger(__name__)


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", case_sensitive=False)
    """Application settings loaded from environment variables."""

    # === APP ===
    secret_key: str
    jwt_expiry_minutes: int = 60
    environment: str = "development"

    # === DATABASE ===
    db_primary_url: str
    db_replica_url: str
    db_pool_min: int = 5
    db_pool_max: int = 20
    db_pool_timeout_seconds: int = 30

    # === REDIS ===
    redis_url: str
    cache_default_ttl: int = 60

    # === RATE LIMITING ===
    rate_limit_per_minute: int = 60

    # === BRUTE FORCE ===
    brute_force_max_attempts: int = 5
    brute_force_lockout_minutes: int = 15

    # === ENCRYPTION ===
    encryption_key: str
    encrypt_columns: str = "ssn,credit_card"

    # === HONEYPOT ===
    honeypot_tables: str = "secret_keys,admin_passwords"

    # === RBAC ROLES ===
    rbac_roles_json: str = """{
        "admin": {
            "tables": "*",
            "columns": "*",
            "operations": ["SELECT", "INSERT", "UPDATE", "DELETE"]
        },
        "readonly": {
            "tables": "*",
            "columns": "*",
            "operations": ["SELECT"]
        },
        "guest": {
            "tables": ["public_data"],
            "columns": ["id", "name", "created_at"],
            "operations": ["SELECT"]
        }
    }"""

    # === QUERY LIMITS ===
    query_timeout_seconds: int = 5
    admin_query_timeout_seconds: int = 10
    auto_limit_default: int = 1000
    cost_threshold_warn: int = 1000
    cost_threshold_block: int = 10000
    slow_query_threshold_ms: int = 200
    daily_budget_default: int = 50000

    # === CIRCUIT BREAKER ===
    circuit_failure_threshold: int = 5
    circuit_cooldown_seconds: int = 30

    # === AI ===
    openai_api_key: str = ""
    ai_model: str = "gpt-4o-mini"
    ai_enabled: bool = False

    # === WEBHOOKS ===
    webhook_url: str = ""

    @property
    def encrypt_columns_list(self) -> List[str]:
        """Parse comma-separated encryption columns."""
        return [c.strip() for c in self.encrypt_columns.split(",") if c.strip()]

    @property
    def honeypot_tables_list(self) -> List[str]:
        """Parse comma-separated honeypot tables."""
        return [t.strip() for t in self.honeypot_tables.split(",") if t.strip()]

    @property
    def rbac_roles(self) -> dict:
        """Parse RBAC roles from JSON configuration."""
        import json
        try:
            return json.loads(self.rbac_roles_json)
        except json.JSONDecodeError:
            logger.warning("Failed to parse RBAC roles JSON, using defaults")
            return {
                "admin": {"tables": "*", "columns": "*", "operations": ["SELECT", "INSERT", "UPDATE", "DELETE"]},
                "readonly": {"tables": "*", "columns": "*", "operations": ["SELECT"]},
                "guest": {"tables": ["public_data"], "columns": ["id", "name", "created_at"], "operations": ["SELECT"]}
            }


settings = Settings()
