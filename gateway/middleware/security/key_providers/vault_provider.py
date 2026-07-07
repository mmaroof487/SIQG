from .base import KeyProvider

class VaultProvider(KeyProvider):
    async def get_master_key(self) -> bytes:
        raise NotImplementedError("VaultProvider not yet implemented.")
        
    async def rotate_master_key(self) -> bytes:
        raise NotImplementedError("VaultProvider not yet implemented.")
