"""认证相关路由"""
from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user
from ..models import User
from .. import schemas
from ..services import user_service

router = APIRouter()


@router.post("/register", response_model=schemas.UserInfo)
def register(payload: schemas.UserRegister, db: Session = Depends(get_db)):
    return user_service.create_user(
        db,
        username=payload.username,
        password=payload.password,
        email=payload.email,
    )


@router.post("/login", response_model=schemas.TokenResp)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = user_service.authenticate_user(db, form.username, form.password)
    token = user_service.make_token(user)
    return schemas.TokenResp(
        access_token=token,
        token_type="bearer",
        username=user.username,
        role=user.role.value,
    )


@router.post("/change-password", response_model=schemas.SuccessResp)
def change_password(
    payload: schemas.ChangePassword,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_service.change_user_password(db, current_user, payload.old_password, payload.new_password)
    return schemas.SuccessResp(message="密码已修改")
