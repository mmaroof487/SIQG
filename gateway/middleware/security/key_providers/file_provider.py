import os
import hashlib
from .base import KeyProvider
from utils.logger import get_logger

logger = get_logger(__name__)

class FileProvider(KeyProvider):
    def __init__(self, filepath: str = "~/.argus/master.key"):
        self.filepath = os.path.expanduser(filepath)
        
    async def get_master_key(self) -> bytes:
        if not os.path.exists(self.filepath):
            logger.critical(
                f"Master key file not found at {self.filepath}! Generating a new one. "
                "WARNING: If previous encrypted data exists, it is now permanently unrecoverable."
            )
            os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
            new_key = os.urandom(32)
            with open(self.filepath, "wb") as f:
                f.write(new_key)
            os.chmod(self.filepath, 0o600)
            return new_key
            
        with open(self.filepath, "rb") as f:
            raw_key = f.read().strip()
            
        if len(raw_key) == 32:
            return raw_key
        return hashlib.sha256(raw_key).digest()

    async def rotate_master_key(self) -> bytes:
        new_key = os.urandom(32)
        with open(self.filepath, "wb") as f:
            f.write(new_key)
        os.chmod(self.filepath, 0o600)
        return new_key
