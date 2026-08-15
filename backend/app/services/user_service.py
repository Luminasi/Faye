"""用户服务层"""
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..models import User, UserRole
from ..utils.security import hash_password, verify_password, create_access_token
from ..utils.logger import get_logger

logger = get_logger("user_service")


def create_user(db: Session, *, username: str, password: str, email: str | None = None, role: UserRole = UserRole.USER) -> User:
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户名已被注册")
    if email and db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="邮箱已被注册")
    user = User(
        username=username,
        email=email,
        password_hash=hash_password(password),
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("user_created", user_id=user.id, username=user.username, role=role.value)
    return user


def authenticate_user(db: Session, username: str, password: str) -> User:
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用")
    return user


def make_token(user: User) -> str:
    # RFC 7519 规定 JWT "sub" 必须是字符串；python-jose 会严格校验
    return create_access_token(
        data={
            "sub": str(user.id),
            "username": user.username,
            "role": user.role.value,
        }
    )


def change_user_password(db: Session, user: User, old_password: str, new_password: str) -> None:
    if not verify_password(old_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="旧密码不正确")
    user.password_hash = hash_password(new_password)
    db.commit()
    logger.info("password_changed", user_id=user.id, username=user.username)
