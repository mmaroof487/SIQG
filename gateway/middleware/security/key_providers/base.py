from typing import Protocol

class KeyProvider(Protocol):
    async def get_master_key(self) -> bytes:
        """Retrieve the master key bytes. Should return exactly 32 bytes."""
        ...
        
    async def rotate_master_key(self) -> bytes:
        """Rotate the master key and return the new 32 bytes."""
        ...
