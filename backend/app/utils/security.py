from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from jose import JWTError, jwt
import bcrypt

from ..config import get_settings
from .logger import get_logger

logger = get_logger("security")
settings = get_settings()


def hash_password(password: str) -> str:
    """Hash a plaintext password with bcrypt (4.x recommended rounds)."""
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash (constant-time)."""
    try:
        pwd_bytes = plain_password.encode("utf-8")
        hash_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(pwd_bytes, hash_bytes)
    except Exception as e:
        # Handles malformed hash strings etc. without exposing details in logs
        logger.debug(
            "verify_password_failed_safe",
            err=type(e).__name__,
        )
        return False


def create_access_token(data: dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    token = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token


def decode_token(token: str) -> Optional[dict[str, Any]]:
    try:
        return jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            # default is verify_exp=True; explicitly written for future extension
            options={"verify_exp": True, "verify_aud": False, "require": []},
        )
    except JWTError as e:
        logger.debug("jwt_decode_failed", err=type(e).__name__, msg=str(e))
        return None
    except Exception as e:
        logger.warning("jwt_decode_unexpected", err=type(e).__name__, msg=str(e))
        return None
