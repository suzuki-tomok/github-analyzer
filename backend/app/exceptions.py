# app/exceptions.py
from fastapi import Request
from fastapi.responses import JSONResponse
from enum import Enum

from app.schemas.response.common import ErrorResponse
from app.logger import logger


class ErrorCode(str, Enum):
    """エラーコード一覧"""

    # 認証系
    INVALID_TOKEN = "INVALID_TOKEN"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    USER_NOT_FOUND = "USER_NOT_FOUND"
    GITHUB_AUTH_FAILED = "GITHUB_AUTH_FAILED"

    # リクエスト系
    INVALID_REPO_URL = "INVALID_REPO_URL"
    INVALID_REQUEST = "INVALID_REQUEST"

    # リソース系
    ANALYSIS_NOT_FOUND = "ANALYSIS_NOT_FOUND"

    # 外部API系
    GITHUB_API_ERROR = "GITHUB_API_ERROR"
    GEMINI_API_ERROR = "GEMINI_API_ERROR"

    # サーバー系
    INTERNAL_ERROR = "INTERNAL_ERROR"


class AppException(Exception):
    """アプリケーション共通の例外"""

    def __init__(self, status_code: int, code: ErrorCode, message: str):
        self.status_code = status_code
        self.code = code
        self.message = message


async def app_exception_handler(request: Request, exc: AppException):
    """AppExceptionを統一形式でレスポンス"""
    # エラーログ出力
    logger.warning(
        f"AppException | {exc.code.value} | {exc.status_code} | {exc.message}"
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "code": exc.code.value,
            "message": exc.message,
        },
    )


# Swagger用の共通レスポンス定義
error_responses = {
    400: {"model": ErrorResponse, "description": "Bad Request"},
    401: {"model": ErrorResponse, "description": "Unauthorized"},
    404: {"model": ErrorResponse, "description": "Not Found"},
    500: {"model": ErrorResponse, "description": "Internal Server Error"},
}
