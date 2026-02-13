# app/main.py
from fastapi import FastAPI

from app.routers import auth, analyses
from app.exceptions import AppException, app_exception_handler
from app.middleware import LoggingMiddleware
from app.logger import logger
from app.config import settings

app = FastAPI(
    title="github-analyzer",
    description="GitHubリポジトリを分析してスコアとレポートを生成",
    version="0.1.0",
)

# ミドルウェア登録
app.add_middleware(LoggingMiddleware)

# 例外ハンドラ登録
app.add_exception_handler(AppException, app_exception_handler)

# ルーター登録
app.include_router(auth.router)
app.include_router(analyses.router)

# 起動ログ
logger.info("=" * 50)
logger.info("github-analyzer v0.1.0")
logger.info(f"Database: {settings.database_url}")
logger.info(f"Gemini Model: {settings.gemini_model}")
logger.info("=" * 50)


@app.get("/")
def root():
    return {"message": "github-analyzer API"}
