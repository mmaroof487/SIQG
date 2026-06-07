"""Authentication router - Login and token generation."""
import re
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from middleware.security.auth import (
    create_jwt,
    verify_password,
    hash_password,
)
from middleware.security.brute_force import (
    check_brute_force,
    record_failed_attempt,
    record_successful_attempt,
)
from models import User, Role
from utils.db import PrimarySession
from utils.logger import get_logger

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])
logger = get_logger(__name__)

# Regex: alphanumeric + underscore + hyphen, 3–32 chars
_USERNAME_RE = re.compile(r'^[a-zA-Z0-9_-]{3,32}$')
# Basic email regex
_EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


class LoginRequest(BaseModel):
    username: str
    password: str

    @field_validator("username", "password", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str

    @field_validator("username", mode="before")
    @classmethod
    def validate_username(cls, v: str) -> str:
        v = v.strip() if isinstance(v, str) else v
        if not _USERNAME_RE.match(v):
            raise ValueError(
                "Username must be 3–32 characters and contain only letters, "
                "numbers, underscores, or hyphens."
            )
        return v

    @field_validator("email", mode="before")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower() if isinstance(v, str) else v
        if not _EMAIL_RE.match(v):
            raise ValueError("Invalid email address format.")
        if len(v) > 254:
            raise ValueError("Email address is too long.")
        return v

    @field_validator("password", mode="before")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("Password must be a string.")
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters.")
        if len(v) > 128:
            raise ValueError("Password must not exceed 128 characters.")
        if not re.search(r'[A-Za-z]', v):
            raise ValueError("Password must contain at least one letter.")
        if not re.search(r'[0-9]', v):
            raise ValueError("Password must contain at least one number.")
        return v


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


@router.post("/login", response_model=TokenResponse)
async def login(request: Request, credentials: LoginRequest):
    """
    Login with username/password and get JWT token.
    """
    # Check brute force protection (IP + username keyed)
    await check_brute_force(request, credentials.username)

    # Find user in DB
    async with PrimarySession() as session:
        stmt = select(User).where(User.username == credentials.username)
        result = await session.execute(stmt)
        user = result.scalars().first()

    # Use identical error message for missing user vs bad password
    # to prevent username enumeration attacks
    if not user:
        await record_failed_attempt(request, credentials.username)
        logger.warning(f"Login failed: user not found - {credentials.username}")
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Reject deactivated accounts
    if not user.is_active:
        logger.warning(f"Login failed: account disabled - {credentials.username}")
        raise HTTPException(status_code=403, detail="Account is disabled. Contact an administrator.")

    # Verify password
    if not verify_password(credentials.password, user.hashed_password):
        await record_failed_attempt(request, credentials.username)
        logger.warning(f"Login failed: invalid password - {credentials.username}")
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Clear brute force counter on successful login
    await record_successful_attempt(request, credentials.username)

    # Ensure role is passed as a plain string (handles both enum and str)
    role_value = user.role.value if hasattr(user.role, "value") else str(user.role)
    token = create_jwt(str(user.id), role_value)

    logger.info(f"Login successful: {credentials.username} (role={role_value})")

    return TokenResponse(
        access_token=token,
        role=role_value,
    )


@router.post("/register", response_model=TokenResponse)
async def register(request: Request, data: RegisterRequest):
    """
    Register a new user (creates as 'readonly' by default).
    Pydantic validators on RegisterRequest enforce username/email/password rules.
    """
    # Hash password
    hashed = hash_password(data.password)

    # Try to create user
    try:
        async with PrimarySession() as session:
            # Check if username OR email is already taken
            stmt = select(User).where(
                (User.username == data.username) | (User.email == data.email)
            )
            result = await session.execute(stmt)
            existing = result.scalars().first()
            if existing:
                # Don't reveal which field is taken (prevents enumeration)
                raise HTTPException(
                    status_code=400,
                    detail="An account with that username or email already exists."
                )

            user = User(
                username=data.username,
                email=data.email,
                hashed_password=hashed,
                role=Role.readonly,  # Use enum, not bare string
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

            # Ensure role is a plain string
            role_value = user.role.value if hasattr(user.role, "value") else str(user.role)
            token = create_jwt(str(user.id), role_value)
            logger.info(f"New user registered: {data.username} (role={role_value})")

            return TokenResponse(
                access_token=token,
                role=role_value,
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(status_code=500, detail="Registration failed")


# Grace period: allow refresh within this many seconds AFTER token expiry
_REFRESH_GRACE_SECONDS = 300  # 5 minutes


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: Request):
    """
    Renew an existing JWT token.

    Accepts tokens that are expired within the grace period (5 minutes).
    Validates the signature and confirms the user still exists and is active in DB.
    """
    from jose import jwt as jose_jwt, JWTError
    from config import settings as _settings

    # Extract token from Authorization header
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = auth_header[len("Bearer "):].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Empty token")

    # Decode token without expiry enforcement so we can check the grace window
    try:
        payload = jose_jwt.decode(
            token,
            _settings.secret_key,
            algorithms=["HS256"],
            options={"verify_exp": False},  # We check expiry manually below
        )
    except JWTError as e:
        logger.warning(f"Token refresh: invalid signature: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = payload.get("sub")
    exp = payload.get("exp")
    if not user_id or not exp:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    import time as _time
    now = _time.time()
    if now > exp + _REFRESH_GRACE_SECONDS:
        logger.warning(
            f"Token refresh rejected: token expired {int(now - exp)}s ago "
            f"(grace={_REFRESH_GRACE_SECONDS}s), user={user_id}"
        )
        raise HTTPException(
            status_code=401,
            detail="Token has expired. Please log in again."
        )

    # Confirm user still exists and is active in DB
    async with PrimarySession() as session:
        import uuid as _uuid
        try:
            uid = _uuid.UUID(user_id)
        except ValueError:
            raise HTTPException(status_code=401, detail="Invalid token subject")
        stmt = select(User).where(User.id == uid)
        result = await session.execute(stmt)
        user = result.scalars().first()

    if not user:
        logger.warning(f"Token refresh failed: user {user_id} no longer exists")
        raise HTTPException(status_code=401, detail="User no longer exists")

    if not user.is_active:
        logger.warning(f"Token refresh failed: account disabled {user_id}")
        raise HTTPException(status_code=403, detail="Account is disabled.")

    # Issue a fresh token with updated role (role may have changed since original token)
    role_value = user.role.value if hasattr(user.role, "value") else str(user.role)
    new_token = create_jwt(str(user.id), role_value)
    logger.info(f"Token refreshed for: {user.username} (role={role_value})")

    return TokenResponse(
        access_token=new_token,
        role=role_value,
    )
