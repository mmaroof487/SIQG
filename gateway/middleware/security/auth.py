"""Authentication middleware - JWT and API key validation."""
import hashlib
import hmac
import time
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from config import settings
from utils.logger import get_logger
import json

logger = get_logger(__name__)
security = HTTPBearer(auto_error=False)

# Password hashing context - bcrypt only (no deprecated schemes)
pwd_context = CryptContext(schemes=["bcrypt"])


def create_jwt(user_id: str, role: str) -> str:
    """Create a JWT token."""
    payload = {
        "sub": user_id,
        "role": role,
        "exp": datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=settings.jwt_expiry_minutes),
        "iat": datetime.now(timezone.utc).replace(tzinfo=None),
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





async def validate_api_key_scope(request: Request, query: str, extracted_tables: list[str]) -> None:
    """
    Validate that the query respects API key scoping restrictions.
    Raises HTTPException if scoping is violated.
    """
    api_key_scope = getattr(request.state, "api_key_scope", None)
    if not api_key_scope:
        # Not an API key auth, or no scoping restrictions
        return

    allowed_tables = api_key_scope.get("allowed_tables")
    allowed_query_types = api_key_scope.get("allowed_query_types")

    # Check allowed tables (whitelist)
    if allowed_tables is not None and isinstance(allowed_tables, list):
        for table in extracted_tables:
            if table not in allowed_tables:
                raise HTTPException(
                    status_code=403,
                    detail={
                        "blocked": True,
                        "block_reasons": [f"API key does not have access to table: {table}"],
                        "suggested_fix": f"This API key is restricted to tables: {', '.join(allowed_tables)}",
                    }
                )

    # Check allowed query types (whitelist)
    if allowed_query_types is not None and isinstance(allowed_query_types, list):
        query_upper = query.strip().upper()
        # Extract query type (first word)
        query_type = query_upper.split()[0] if query_upper else ""

        # Map common multi-word query types
        if query_upper.startswith("WITH"):
            query_type = "WITH"  # CTE

        if query_type and query_type not in allowed_query_types:
            raise HTTPException(
                status_code=403,
                detail={
                    "blocked": True,
                    "block_reasons": [f"API key does not allow {query_type} operations"],
                    "suggested_fix": f"This API key is restricted to: {', '.join(allowed_query_types)}",
                }
            )


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """
    Dependency to get current authenticated user.
    Tries JWT first, then API key (with cache + DB fallback).
    For API keys, also retrieves scoping restrictions (allowed tables, query types).
    """
    # Try JWT Bearer token from cookie first, then Authorization header
    token = request.cookies.get("token")
    if not token and credentials:
        token = credentials.credentials

    if token:
        try:
            payload = decode_jwt(token)
            request.state.user_id = payload["sub"]
            request.state.role = payload["role"]
            request.state.auth_type = "jwt"
            # JWT doesn't have scoping restrictions
            request.state.api_key_scope = None
            return payload
        except HTTPException:
            pass

    # Try API key from X-API-Key header
    api_key = request.headers.get("X-API-Key")
    if api_key:
        key_hash = hash_api_key(api_key)
        redis = request.app.state.redis

        # Try Redis cache first (fast path)
        try:
            cached = await redis.get(f"apikey:{key_hash}")
            if cached:
                user_data = json.loads(cached)
                request.state.user_id = user_data["user_id"]
                request.state.role = user_data["role"]
                request.state.auth_type = "api_key"
                # Extract scoping info from cache
                request.state.api_key_scope = {
                    "allowed_tables": user_data.get("allowed_tables"),
                    "allowed_query_types": user_data.get("allowed_query_types"),
                    "rate_limit_override": user_data.get("rate_limit_override"),
                }
                return user_data
        except Exception as e:
            logger.warning(f"Redis lookup failed for API key: {e}")

        # Fall back to database lookup
        try:
            from utils.db import PrimarySession
            async with PrimarySession() as session:
                # Query database for API key (stored as hash)
                from sqlalchemy import select
                from models import APIKey

                stmt = select(APIKey).where(APIKey.key_hash == key_hash)
                result = await session.execute(stmt)
                api_key_record = result.scalars().first()

                if api_key_record:
                    # Get user info from the foreign key
                    from models import User
                    user_stmt = select(User).where(User.id == api_key_record.user_id)
                    user_result = await session.execute(user_stmt)
                    user_record = user_result.scalars().first()

                    if user_record:
                        user_data = {
                            "user_id": str(api_key_record.user_id),
                            "role": user_record.role.value,
                            "allowed_tables": api_key_record.allowed_tables,
                            "allowed_query_types": api_key_record.allowed_query_types,
                            "rate_limit_override": api_key_record.rate_limit_override,
                        }
                        request.state.user_id = user_data["user_id"]
                        request.state.role = user_data["role"]
                        request.state.auth_type = "api_key"
                        request.state.api_key_scope = {
                            "allowed_tables": api_key_record.allowed_tables,
                            "allowed_query_types": api_key_record.allowed_query_types,
                            "rate_limit_override": api_key_record.rate_limit_override,
                        }

                        # Cache for next time
                        try:
                            await redis.setex(
                                f"apikey:{key_hash}",
                                3600,  # Cache for 1 hour
                                json.dumps(user_data, default=str)
                            )
                        except Exception:
                            pass  # Cache write error is not critical

                        return user_data
        except Exception as e:
            logger.warning(f"Database lookup failed for API key: {e}")

        # API key not found in cache or DB
        raise HTTPException(status_code=401, detail="Invalid API key")

    raise HTTPException(
        status_code=401,
        detail="No credentials provided. Use 'Authorization: Bearer <token>' or 'X-API-Key: <key>'"
    )

