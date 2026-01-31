# app/dependencies/auth.py
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import jwt, JWTError

from app.config import settings
from app.models import User
from app.dependencies.database import get_db
from app.exceptions import AppException, ErrorCode

# HTTPヘッダーからBearerトークンを取得するためのセキュリティスキーム
security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """
    JWTトークンを検証し、現在のユーザーを取得する
    """
    token = credentials.credentials

    try:
        # JWTをデコードしてペイロードを取得
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=["HS256"])
        user_id = payload.get("sub")
        if user_id is None:
            raise AppException(
                401, ErrorCode.INVALID_TOKEN, "Invalid token: user_id not found"
            )
    except JWTError:
        # トークンが不正または期限切れ
        raise AppException(401, ErrorCode.INVALID_TOKEN, "Invalid or expired token")

    # DBからユーザーを取得
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise AppException(401, ErrorCode.USER_NOT_FOUND, "User not found")

    return user
