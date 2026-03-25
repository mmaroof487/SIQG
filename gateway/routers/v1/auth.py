"""Authentication router - Login and token generation."""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from datetime import datetime
from middleware.security.auth import (
    create_jwt,
    verify_password,
    hash_password,
    record_failed_attempt,
    record_successful_attempt,
    check_brute_force,
)
from middleware.security.brute_force import check_brute_force
from models import User
from utils.db import PrimarySession
from utils.logger import get_logger

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])
logger = get_logger(__name__)


class LoginRequest(BaseModel):
    username: str
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
        result = await session.execute(
            "SELECT * FROM users WHERE username = %s",
            (credentials.username,),
        )
        user = result.mappings().first() if result else None

    if not user:
        await record_failed_attempt(request, credentials.username)
        logger.warning(f"Login failed: user not found - {credentials.username}")
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Verify password
    if not verify_password(credentials.password, user["hashed_password"]):
        await record_failed_attempt(request, credentials.username)
        logger.warning(f"Login failed: invalid password - {credentials.username}")
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Clear brute force attempts on success
    await record_successful_attempt(request, credentials.username)

    # Create token
    token = create_jwt(str(user["id"]), user["role"])

    logger.info(f"Login successful: {credentials.username} ({user['role']})")

    return TokenResponse(
        access_token=token,
        role=user["role"],
    )


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


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
            stmt = "SELECT id FROM users WHERE username = %s OR email = %s"
            result = await session.execute(stmt, (data.username, data.email))
            if result.fetchone():
                raise HTTPException(status_code=400, detail="User already exists")

            user = User(
                username=data.username,
                email=data.email,
                hashed_password=hashed,
                role="readonly",  # Default role
            )
            session.add(user)
            await session.commit()

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
            session.add(user)
            await session.commit()
            await session.refresh(user)
        except Exception as e:
            logger.warning(f"Registration failed: {e}")
            raise HTTPException(status_code=400, detail="Username or email already exists")

    # Create token
    token = create_jwt(str(user.id), user.role)

    logger.info(f"Registration successful: {data.username}")

    return TokenResponse(
        access_token=token,
        role=user.role,
    )
