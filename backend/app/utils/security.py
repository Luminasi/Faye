from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from ..config import get_settings
from .logger import get_logger

logger = get_logger("security")
settings = get_settings()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


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
            # options 默认 verify_exp=True；显式写出来便于以后扩展
            options={"verify_exp": True, "verify_aud": False, "require": []},
        )
    except JWTError as e:
        logger.debug("jwt_decode_failed", err=type(e).__name__, msg=str(e))
        return None
    except Exception as e:
        logger.warning("jwt_decode_unexpected", err=type(e).__name__, msg=str(e))
        return None
