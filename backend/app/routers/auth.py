# app/routers/auth.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import httpx
from jose import jwt
from datetime import datetime, timedelta

from app.config import settings
from app.dependencies import get_db, get_current_user
from app.models import User
from app.schemas import SuccessResponse
from app.exceptions import AppException, ErrorCode, error_responses
from app.logger import logger

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)

GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"


@router.post(
    "/github/callback",
    responses={400: error_responses[400]},
)
async def github_callback(code: str, db: Session = Depends(get_db)):
    """
    GitHub OAuth コールバック処理
    """
    logger.info("Auth | GitHub callback started")

    # 1. codeでGitHubアクセストークン取得
    async with httpx.AsyncClient() as client:
        response = await client.post(
            GITHUB_TOKEN_URL,
            data={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code,
            },
            headers={"Accept": "application/json"},
        )

    token_data = response.json()
    access_token = token_data.get("access_token")

    if not access_token:
        logger.warning("Auth | Failed to get access token from GitHub")
        raise AppException(
            400, ErrorCode.GITHUB_AUTH_FAILED, "Failed to get access token from GitHub"
        )

    logger.debug("Auth | GitHub access token obtained")

    # 2. GitHubユーザー情報取得
    async with httpx.AsyncClient() as client:
        response = await client.get(
            GITHUB_USER_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )

    github_user = response.json()
    github_id = github_user.get("id")
    github_username = github_user.get("login")

    if not github_id:
        logger.warning("Auth | Failed to get user info from GitHub")
        raise AppException(
            400, ErrorCode.GITHUB_AUTH_FAILED, "Failed to get user info from GitHub"
        )

    logger.debug(f"Auth | GitHub user: {github_username}")

    # 3. DB確認（なければ作成、あれば更新）
    user = db.query(User).filter(User.github_id == github_id).first()

    if not user:
        user = User(
            github_id=github_id,
            github_username=github_username,
            github_access_token=access_token,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"Auth | New user created: {github_username}")
    else:
        user.github_access_token = access_token
        db.commit()
        logger.info(f"Auth | User login: {github_username}")

    # 4. JWT発行
    expire = datetime.utcnow() + timedelta(days=7)
    payload = {"sub": user.id, "exp": expire}
    jwt_token = jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")

    logger.info(f"Auth | JWT issued for user: {user.id}")

    return SuccessResponse(
        data={
            "access_token": jwt_token,
            "token_type": "bearer",
        }
    )


@router.get(
    "/me",
    responses={401: error_responses[401]},
)
def get_me(current_user: User = Depends(get_current_user)):
    """
    現在ログイン中のユーザー情報を取得
    """
    logger.debug(f"Auth | Get me: {current_user.github_username}")

    return SuccessResponse(
        data={
            "id": current_user.id,
            "github_username": current_user.github_username,
        }
    )
