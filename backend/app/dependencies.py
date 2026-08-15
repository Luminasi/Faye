"""FastAPI 依赖注入：用户认证、权限校验等"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .database import get_db
from .models import User, UserRole
from .utils.logger import get_logger
from .utils.security import decode_token

logger = get_logger("auth")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    if not token:
        logger.warning("auth_missing_token")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录或Token无效")

    payload = decode_token(token)
    if not payload:
        logger.warning("auth_decode_failed", token_preview=token[:20] + "...")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token已过期或无效")

    sub_raw = payload.get("sub")
    # 兼容 sub 可能是字符串或整数（不同 JOSE 实现/缓存场景）
    if sub_raw is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token内容无效")
    try:
        user_id: int = int(sub_raw)
    except (ValueError, TypeError):
        logger.warning("auth_sub_invalid", sub=repr(sub_raw))
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token内容无效")

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        logger.warning("auth_user_not_found", user_id=user_id, active=None if not user else user.is_active)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在或已禁用")
    return user


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")
    return current_user
