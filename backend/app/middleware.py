# app/middleware.py
import time
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.logger import logger


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    リクエスト/レスポンスをログに記録するミドルウェア
    """

    async def dispatch(self, request: Request, call_next):
        # リクエスト開始時刻
        start_time = time.time()

        # リクエスト情報
        method = request.method
        path = request.url.path
        client_ip = request.client.host if request.client else "unknown"

        # リクエストログ
        logger.info(f"Request  | {method} {path} | IP: {client_ip}")

        # 処理実行
        try:
            response = await call_next(request)
        except Exception as e:
            # 予期せぬエラー
            logger.error(f"Error    | {method} {path} | {type(e).__name__}: {str(e)}")
            raise

        # 処理時間計算
        process_time = time.time() - start_time
        process_time_ms = round(process_time * 1000, 2)

        # レスポンスログ
        status_code = response.status_code
        log_level = logging.INFO if status_code < 400 else logging.WARNING
        logger.log(
            log_level,
            f"Response | {method} {path} | {status_code} | {process_time_ms}ms",
        )

        return response
