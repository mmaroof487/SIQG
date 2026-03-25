"""Authentication middleware - JWT and API key validation."""
import hashlib
from datetime import datetime, timedelta
from fastapi import HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from config import settings
from utils.logger import get_logger
import json

logger = get_logger(__name__)
security = HTTPBearer(auto_error=False)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_jwt(user_id: str, role: str) -> str:
    """Create a JWT token."""
    payload = {
        "sub": user_id,
        "role": role,
        "exp": datetime.utcnow() + timedelta(minutes=settings.jwt_expiry_minutes),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def decode_jwt(token: str) -> dict:
    """Decode and validate JWT token."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        return payload
    except JWTError as e:
        logger.error(f"JWT decode error: {e}")
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def hash_password(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a password against hash."""
    return pwd_context.verify(plain, hashed)


def hash_api_key(raw_key: str) -> str:
    """Hash an API key using SHA-256."""
    return hashlib.sha256(raw_key.encode()).hexdigest()


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """
    Dependency to get current authenticated user.
    Tries JWT first, then API key.
    """
    # Try JWT Bearer token first
    if credentials:
        payload = decode_jwt(credentials.credentials)
        request.state.user_id = payload["sub"]
        request.state.role = payload["role"]
        request.state.auth_type = "jwt"
        return payload

    # Try API key from X-API-Key header
    api_key = request.headers.get("X-API-Key")
    if api_key:
        key_hash = hash_api_key(api_key)
        redis = request.app.state.redis
        
        # Try Redis cache first (fast path)
        cached = await redis.get(f"apikey:{key_hash}")
        if cached:
            user_data = json.loads(cached)
            request.state.user_id = user_data["user_id"]
            request.state.role = user_data["role"]
            request.state.auth_type = "api_key"
            return user_data
        
        # In production, would check DB here
        # For now, reject if not cached
        raise HTTPException(status_code=401, detail="Invalid API key")

    raise HTTPException(
        status_code=401,
        detail="No credentials provided. Use 'Authorization: Bearer <token>' or 'X-API-Key: <key>'"
    )
