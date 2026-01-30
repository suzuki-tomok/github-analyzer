# app/dependencies/database.py
from typing import Generator
from sqlalchemy.orm import Session

from app.database import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """
    DBセッションを取得するジェネレータ
    - リクエストごとにセッションを作成
    - 処理終了後に自動でクローズ
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()