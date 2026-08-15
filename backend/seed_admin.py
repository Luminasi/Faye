"""独立脚本：手动初始化管理员账号（可选，一般由启动事件自动完成）"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.config import get_settings
from app.database import SessionLocal, Base, engine
from app.models import User, UserRole
from app.utils.security import hash_password

settings = get_settings()

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == settings.ADMIN_USERNAME).first()
        if admin:
            print(f"[SKIP] Admin '{settings.ADMIN_USERNAME}' already exists (id={admin.id})")
        else:
            admin = User(
                username=settings.ADMIN_USERNAME,
                email=settings.ADMIN_EMAIL,
                password_hash=hash_password(settings.ADMIN_PASSWORD),
                role=UserRole.ADMIN,
                is_active=True,
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)
            print(f"[OK] Admin created: id={admin.id}, user={settings.ADMIN_USERNAME}")
    finally:
        db.close()
