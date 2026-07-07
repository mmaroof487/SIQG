from typing import Optional
from .base import KeyProvider
from config import settings
import os
import hashlib
from utils.logger import get_logger

logger = get_logger(__name__)

class EnvProvider(KeyProvider):
    async def get_master_key(self) -> bytes:
        raw_key = os.environ.get("MASTER_KEY", os.environ.get("ENCRYPTION_KEY", ""))
        if not raw_key:
            if settings.environment == "development":
                logger.warning(
                    "MASTER_KEY not set — using insecure development key. "
                    "Set MASTER_KEY in your environment for any real data."
                )
                raw_key = "argus_dev_only_key_not_for_production"
            else:
                raise RuntimeError(
                    "MASTER_KEY environment variable is not set. "
                    "Cannot start in a non-development environment without a master key. "
                    "Set MASTER_KEY to a secure 32-byte hex value."
                )
        raw_bytes = raw_key.encode("utf-8")
        if len(raw_bytes) == 32:
            return raw_bytes
        return hashlib.sha256(raw_bytes).digest()

    async def rotate_master_key(self) -> bytes:
        raise NotImplementedError("EnvProvider does not support master key rotation.")
