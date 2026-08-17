"""FastAPI 应用入口"""
import os
import traceback
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import get_settings
from .database import Base, engine, SessionLocal
from .dependencies import get_current_user
from .models import ChatSession, DocStatus, Document, KnowledgeBase, User, UserRole
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


# ======================================================================
# GLOBAL EXCEPTION HANDLER — 500s are now always traceable
# ======================================================================
@app.exception_handler(Exception)
async def _global_exception_handler(request: Request, exc: Exception):
    tb_str = traceback.format_exc()
    # Always log full traceback server-side (even in production)
    logger.error(
        "unhandled_exception_500",
        method=request.method,
        url=str(request.url),
        exc_type=type(exc).__name__,
        exc_msg=str(exc),
        traceback=tb_str,
    )

    body: dict = {
        "detail": f"Server error ({type(exc).__name__}). Please check backend logs.",
        "error": type(exc).__name__,
    }
    # In dev mode, expose traceback and request URL in the response body so the
    # user can just press F12 -> Network -> 500 entry -> Response and see WHY.
    if settings.APP_DEBUG:
        body["request"] = f"{request.method} {request.url.path}"
        body["traceback"] = tb_str.splitlines()

    # HTTPExceptions already carry a proper status code; preserve it.
    code = getattr(exc, "status_code", status.HTTP_500_INTERNAL_SERVER_ERROR)
    try:
        code = int(code)
    except Exception:
        code = status.HTTP_500_INTERNAL_SERVER_ERROR

    return JSONResponse(status_code=code, content=body)


@app.on_event("startup")
def on_startup():
    # 1. Create required dirs
    db_file_path = settings.DATABASE_URL.replace("sqlite:///", "")
    for d in (
        settings.UPLOAD_DIR,
        settings.CHROMA_PERSIST_DIR,
        os.path.dirname(db_file_path) or ".",
    ):
        Path(d).mkdir(parents=True, exist_ok=True)

    # 2. Create tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized")

    # 3. Admin user bootstrap (idempotent create + repair)
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
            changed = False
            if admin.role != UserRole.ADMIN:
                admin.role = UserRole.ADMIN
                changed = True
            try:
                pw_ok = verify_password(settings.ADMIN_PASSWORD, admin.password_hash)
            except Exception:
                pw_ok = False
            if not pw_ok:
                admin.password_hash = hash_password(settings.ADMIN_PASSWORD)
                changed = True
            if not admin.is_active:
                admin.is_active = True
                changed = True
            if changed:
                db.commit()
                logger.info(f"Admin account repaired: {settings.ADMIN_USERNAME}")

        # 4. One-time DB hygiene sweep: fix legacy rows where (a) user role is NULL / unknown
        #    enum value, (b) session default_kb_ids has non-list JSON, (c) document status bad.
        fixed_users = 0
        for u in db.query(User).all():
            u_changed = False
            if u.role not in (UserRole.ADMIN, UserRole.USER):
                u.role = UserRole.USER if (u.username != settings.ADMIN_USERNAME) else UserRole.ADMIN
                u_changed = True
            if u.is_active is None:
                u.is_active = True
                u_changed = True
            if u_changed:
                fixed_users += 1
        fixed_sessions = 0
        for s in db.query(ChatSession).all():
            val = s.default_kb_ids
            if val is None:
                continue
            if not isinstance(val, list):
                s.default_kb_ids = None
                fixed_sessions += 1
                continue
            cleaned = []
            for item in val:
                try:
                    cleaned.append(int(item))
                except (ValueError, TypeError):
                    pass
            if cleaned != val:
                s.default_kb_ids = cleaned or None
                fixed_sessions += 1
        fixed_docs = 0
        for d in db.query(Document).all():
            d_changed = False
            # 注意：SQLAlchemy Enum 列读出的是 DocStatus 枚举成员（str 子类，值为小写如 "ready"），
            # 不能用 .type.enums 的“名称”元组 ("READY",...) 去比较——那样恒为 False，
            # 会把所有正常文档误判为脏数据并重置为 FAILED。
            if d.status is None or d.status not in (
                DocStatus.PROCESSING,
                DocStatus.READY,
                DocStatus.FAILED,
            ):
                d.status = DocStatus.FAILED
                d_changed = True
            if d.chunk_count is None:
                d.chunk_count = 0
                d_changed = True
            if d_changed:
                fixed_docs += 1
        # ensure KnowledgeBase collection_name placeholder (if any) rewritten
        fixed_kbs = 0
        for kb in db.query(KnowledgeBase).all():
            if (not kb.collection_name) or kb.collection_name == "__placeholder__":
                kb.collection_name = f"kb_{kb.id}"
                fixed_kbs += 1
        if any([fixed_users, fixed_sessions, fixed_docs, fixed_kbs]):
            db.commit()
            logger.info(
                "db_hygiene_fixes_applied",
                users=fixed_users,
                sessions=fixed_sessions,
                docs=fixed_docs,
                kbs=fixed_kbs,
            )
        else:
            logger.info("db_hygiene: no dirty rows detected.")
    except Exception as e:
        logger.error("startup_seed_or_hygiene_failed", error=str(e),
                     traceback=traceback.format_exc())
        db.rollback()
    finally:
        db.close()


# ========== Routers ==========
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
    # Defensive: guard against corrupted UserRole enum deserialization
    raw_role = getattr(current_user, "role", None)
    role_val = raw_role.value if raw_role is not None else "user"
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role": role_val,
        "is_active": bool(current_user.is_active),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.APP_DEBUG,
    )
