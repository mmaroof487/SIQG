"""Gateway configuration using pydantic-settings (Pydantic v2+)."""
from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import List
import os
from utils.logger import get_logger

logger = get_logger(__name__)

# === CENTRALIZED SENSITIVE FIELDS ===
# Single source of truth for field names that should never leak in output
SENSITIVE_FIELDS = {
    "hashed_password",
    "password",
    "token",
    "api_key",
    "secret",
    "internal_notes",
}


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

    # === PER-ROLE RATE LIMITS ===
    rate_limit_admin_per_minute: int = 500
    rate_limit_readonly_per_minute: int = 60
    rate_limit_guest_per_minute: int = 10

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

    # === TIME-BASED RBAC ===
    # Note: Disabled for testing (outside of business hours)
    # To enable: set to valid JSON with allowed_hours and timezone
    time_based_rbac_json: str = "{}"  # Empty = disabled for all roles

    # === QUERY LIMITS ===
    query_timeout_seconds: int = 5
    admin_query_timeout_seconds: int = 10
    auto_limit_default: int = 1000
    cost_threshold_warn: int = 1000
    cost_threshold_block: int = 10000
    slow_query_threshold_ms: int = 200
    daily_budget_default: int = 50000

    # === QUERY WHITELIST ===
    whitelist_mode_enabled: bool = False  # If true, only approved query fingerprints execute

    # === CIRCUIT BREAKER ===
    circuit_failure_threshold: int = 5
    circuit_cooldown_seconds: int = 30

    # === AI ===
    ai_provider: str = "mock"  # Options: "mock", "openai", "gemini", "groq"
    openai_api_key: str = ""
    gemini_api_key: str = ""
    groq_api_key: str = ""
    ai_model: str = "gpt-4o-mini"  # For OpenAI
    gemini_model: str = "gemini-2.0-flash"  # For Gemini
    groq_model: str = "llama-3.1-8b-instant"  # For Groq
    ai_enabled: bool = False

    # === SENSITIVE FIELDS ===
    sensitive_fields_csv: str = "hashed_password,password,token,api_key,secret,internal_notes"

    # === WEBHOOKS ===
    webhook_url: str = ""


    @property
    def sensitive_fields(self) -> set[str]:
        """Single source of truth for sensitive field names.

        Returns the centralized SENSITIVE_FIELDS constant combined with
        any additional fields defined in environment config.
        """
        # Start with centralized constant
        fields = SENSITIVE_FIELDS.copy()
        # Add any additional fields from CSV config
        env_fields = {f.strip().lower() for f in self.sensitive_fields_csv.split(",") if f.strip()}
        return fields | env_fields

    @property
    def get_rate_limit_for_role(self) -> dict[str, int]:
        """Return rate limit mapping for each role."""
        return {
            "admin": self.rate_limit_admin_per_minute,
            "readonly": self.rate_limit_readonly_per_minute,
            "guest": self.rate_limit_guest_per_minute,
        }

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

    @property
    def time_based_rbac(self) -> dict:
        """Parse time-based RBAC rules from JSON configuration."""
        import json
        try:
            return json.loads(self.time_based_rbac_json)
        except json.JSONDecodeError:
            logger.warning("Failed to parse time-based RBAC JSON")
            return {}


settings = Settings()
