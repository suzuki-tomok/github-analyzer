# app/logger.py
import logging
import sys
from datetime import datetime


def setup_logger() -> logging.Logger:
    """
    アプリケーション共通のロガーを設定
    """
    logger = logging.getLogger("github-analyzer")
    logger.setLevel(logging.DEBUG)
    
    # 既存のハンドラがあれば削除（重複防止）
    if logger.handlers:
        logger.handlers.clear()
    
    # フォーマット設定
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    
    # コンソール出力
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # ファイル出力（本番用）
    file_handler = logging.FileHandler("app.log", encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger


# シングルトンとして使う
logger = setup_logger()