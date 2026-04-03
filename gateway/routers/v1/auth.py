"""Authentication router - Login and token generation."""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
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
from models import User
from utils.db import PrimarySession
from utils.logger import get_logger

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])
logger = get_logger(__name__)


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


@router.post("/login", response_model=TokenResponse)
async def login(request: Request, credentials: LoginRequest):
    """
    Login with username/password and get JWT token.
    """
    # Check brute force protection
    await check_brute_force(request, credentials.username)

    # Find user in DB
    async with PrimarySession() as session:
        stmt = select(User).where(User.username == credentials.username)
        result = await session.execute(stmt)
        user = result.scalars().first()

    if not user:
        await record_failed_attempt(request, credentials.username)
        logger.warning(f"Login failed: user not found - {credentials.username}")
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Verify password
    if not verify_password(credentials.password, user.hashed_password):
        await record_failed_attempt(request, credentials.username)
        logger.warning(f"Login failed: invalid password - {credentials.username}")
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Clear brute force attempts on success
    await record_successful_attempt(request, credentials.username)

    # Create token
    token = create_jwt(str(user.id), user.role)

    logger.info(f"Login successful: {credentials.username} ({user.role})")

    return TokenResponse(
        access_token=token,
        role=user.role,
    )


@router.post("/register", response_model=TokenResponse)
async def register(request: Request, data: RegisterRequest):
    """
    Register a new user (creates as 'readonly' by default).
    """
    # Validate input
    if len(data.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    # Hash password
    hashed = hash_password(data.password)

    # Try to create user
    try:
        async with PrimarySession() as session:
            # Check if user already exists
            stmt = select(User).where(
                (User.username == data.username) | (User.email == data.email)
            )
            result = await session.execute(stmt)
            if result.scalars().first():
                raise HTTPException(status_code=400, detail="User already exists")

            user = User(
                username=data.username,
                email=data.email,
                hashed_password=hashed,
                role="readonly",  # Default role
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

            # Create token
            token = create_jwt(str(user.id), user.role)
            logger.info(f"New user registered: {data.username}")

            return TokenResponse(
                access_token=token,
                role=user.role,
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(status_code=500, detail="Registration failed")


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: Request):
    """
    Renew an existing JWT token.
    
    Validates the current token, confirms user still exists in DB,
    and issues a fresh token with a new expiry.
    """
    # Extract token from Authorization header
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = auth_header.replace("Bearer ", "")

    # Decode the existing token (will raise 401 if expired/invalid)
    from middleware.security.auth import decode_jwt, create_jwt
    payload = decode_jwt(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    # Confirm user still exists in DB
    async with PrimarySession() as session:
        stmt = select(User).where(User.id == user_id)
        result = await session.execute(stmt)
        user = result.scalars().first()

    if not user:
        logger.warning(f"Token refresh failed: user {user_id} no longer exists")
        raise HTTPException(status_code=401, detail="User no longer exists")

    # Issue a fresh token
    new_token = create_jwt(str(user.id), user.role)
    logger.info(f"Token refreshed for: {user.username}")

    return TokenResponse(
        access_token=new_token,
        role=user.role,
    )
