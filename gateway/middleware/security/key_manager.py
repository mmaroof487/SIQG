import os
import threading
from functools import lru_cache
from time import time
from typing import Optional
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from config import settings
from utils.logger import get_logger

from .key_providers import EnvProvider, FileProvider, VaultProvider, KeyProvider

logger = get_logger(__name__)


class DEKCache:
    """In-process LRU cache for decrypted DEKs. Never leaves process memory."""
    def __init__(self, ttl_seconds: int = 300, max_size: int = 128):
        self._cache: dict[str, tuple[bytes, float]] = {}
        self._ttl = ttl_seconds
        self._max_size = max_size
        self._lock = threading.Lock()
    
    def get(self, connection_id: str, version: int) -> bytes | None:
        key = f"{connection_id}:{version}"
        with self._lock:
            entry = self._cache.get(key)
            if entry and (time() - entry[1]) < self._ttl:
                return entry[0]
            self._cache.pop(key, None)
        return None
    
    def put(self, connection_id: str, version: int, dek: bytes):
        key = f"{connection_id}:{version}"
        with self._lock:
            if len(self._cache) >= self._max_size:
                # Evict oldest
                oldest = min(self._cache, key=lambda k: self._cache[k][1])
                del self._cache[oldest]
            self._cache[key] = (dek, time())
    
    def invalidate(self, connection_id: str):
        with self._lock:
            to_remove = [k for k in self._cache if k.startswith(f"{connection_id}:")]
            for k in to_remove:
                del self._cache[k]


class KeyManager:
    _instance = None
    _instance_lock = threading.Lock()

    def __init__(self):
        self.provider: KeyProvider = self._get_provider(settings.key_provider)
        self.dek_cache = DEKCache()
        self._master_key: Optional[bytes] = None

    @classmethod
    def get_instance(cls) -> "KeyManager":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
        
    def _get_provider(self, provider_type: str) -> KeyProvider:
        if provider_type == "env":
            return EnvProvider()
        elif provider_type == "file":
            return FileProvider()
        elif provider_type == "vault":
            logger.error("VaultProvider is not yet implemented. Falling back to env.")
            return EnvProvider()
        else:
            logger.warning(f"Unknown key_provider '{provider_type}', falling back to env")
            return EnvProvider()

    async def initialize(self):
        """Must be called at startup to load the master key."""
        self._master_key = await self.provider.get_master_key()
        logger.info("Master key loaded into KeyManager.")

    def _derive_key(self, context: str) -> bytes:
        if not self._master_key:
            raise RuntimeError("KeyManager not initialized. Master key is missing.")
        return HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=context.encode(),
        ).derive(self._master_key)

    def get_dek_wrapping_key(self) -> bytes:
        return self._derive_key("argus:dek-wrapping")

    def get_connection_string_key(self) -> bytes:
        # Actually Phase 2 says "Encrypt connection string with DEK (not directly with master key)"
        # But this is here in case we ever need a global connection string key
        return self._derive_key("argus:connection-strings")

    async def get_dek(self, connection_id: str, version: int, encrypted_dek: str) -> bytes:
        """
        Get the DEK for a connection. Checks in-process cache first.
        If cache miss, decrypts the `encrypted_dek` using the wrapping key and caches it.
        """
        cached_dek = self.dek_cache.get(connection_id, version)
        if cached_dek:
            return cached_dek
            
        # Import here to avoid circular imports during startup
        from .encryption import decrypt_value
        wrapping_key = self.get_dek_wrapping_key()
        dek_str = decrypt_value(encrypted_dek, wrapping_key)
        
        try:
            dek = bytes.fromhex(dek_str)
        except ValueError:
            dek = dek_str.encode('utf-8')
            
        self.dek_cache.put(connection_id, version, dek)
        return dek

    async def rotate_dek(self, connection_id: str, old_version: int) -> tuple[int, str]:
        """
        Generate a new DEK for a connection.
        Returns (new_version, new_encrypted_dek).
        """
        new_version = old_version + 1
        new_dek = os.urandom(32)
        
        from .encryption import encrypt_value
        wrapping_key = self.get_dek_wrapping_key()
        new_encrypted_dek = encrypt_value(new_dek.hex(), wrapping_key)
        
        # Cache the new DEK
        self.dek_cache.put(connection_id, new_version, new_dek)
        
        return new_version, new_encrypted_dek

key_manager = KeyManager.get_instance()
