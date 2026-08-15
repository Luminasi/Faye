"""FastAPI 应用入口"""
import os
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .database import Base, engine, SessionLocal
from .dependencies import get_current_user
from .models import User, UserRole
from .utils.logger import setup_logging, get_logger
from .utils.security import hash_password, verify_password

settings = get_settings()
setup_logging(debug=settings.APP_DEBUG)
logger = get_logger("main")

app = FastAPI(title=settings.APP_NAME, debug=settings.APP_DEBUG)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    # 1. 创建必要目录
    db_file_path = settings.DATABASE_URL.replace("sqlite:///", "")
    for d in (
        settings.UPLOAD_DIR,
        settings.CHROMA_PERSIST_DIR,
        os.path.dirname(db_file_path) or ".",
    ):
        Path(d).mkdir(parents=True, exist_ok=True)

    # 2. 创建数据库表
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized")

    # 3. 初始化管理员账号（幂等：不存在则创建，存在则修正 role 和 密码）
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == settings.ADMIN_USERNAME).first()
        if not admin:
            admin = User(
                username=settings.ADMIN_USERNAME,
                email=settings.ADMIN_EMAIL,
                password_hash=hash_password(settings.ADMIN_PASSWORD),
                role=UserRole.ADMIN,
                is_active=True,
            )
            db.add(admin)
            db.commit()
            logger.info(
                f"Admin account created: {settings.ADMIN_USERNAME} / {settings.ADMIN_PASSWORD}"
            )
        else:
            # 修正历史脏数据：确保 admin 一定拥有 ADMIN 角色，且密码与配置一致
            changed = False
            if admin.role != UserRole.ADMIN:
                admin.role = UserRole.ADMIN
                changed = True
            # 如果配置里的 ADMIN_PASSWORD 无法通过当前 hash 校验，则强制重置为配置密码
            try:
                ok = verify_password(settings.ADMIN_PASSWORD, admin.password_hash)
            except Exception:
                ok = False
            if not ok:
                admin.password_hash = hash_password(settings.ADMIN_PASSWORD)
                changed = True
            if not admin.is_active:
                admin.is_active = True
                changed = True
            if changed:
                db.commit()
                logger.info(f"Admin account repaired: {settings.ADMIN_USERNAME}")
    except Exception as e:
        logger.error("Failed to seed admin", error=str(e))
        db.rollback()
    finally:
        db.close()


# ========== 路由注册 ==========
from .routers import auth as router_auth  # noqa: E402
from .routers import sessions as router_sessions  # noqa: E402
from .routers import chat as router_chat  # noqa: E402
from .routers import admin_kb as router_admin_kb  # noqa: E402

app.include_router(router_auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(router_sessions.router, prefix="/api/sessions", tags=["Sessions"])
app.include_router(router_chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(router_admin_kb.router, prefix="/api/admin/kb", tags=["Admin-KB"])


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.APP_NAME}


@app.get("/api/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role.value,
        "is_active": current_user.is_active,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.APP_DEBUG,
    )
