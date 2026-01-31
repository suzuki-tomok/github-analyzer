# tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from jose import jwt
from datetime import datetime, timedelta

from app.main import app
from app.database import Base
from app.dependencies.database import get_db
from app.models import User, Analysis
from app.config import settings


# テスト用インメモリDB
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """テスト用DBセッション（各テストで初期化）"""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """テスト用FastAPIクライアント"""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db_session):
    """テスト用ユーザー"""
    user = User(
        id="test-user-id",
        github_id=12345,
        github_username="testuser",
        github_access_token="dummy_token",
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def other_user(db_session):
    """他人ユーザー（認可テスト用）"""
    user = User(
        id="other-user-id",
        github_id=99999,
        github_username="otheruser",
        github_access_token="dummy_token",
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def auth_header(test_user):
    """認証済みヘッダー"""
    expire = datetime.utcnow() + timedelta(days=1)
    payload = {"sub": test_user.id, "exp": expire}
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def other_auth_header(other_user):
    """他人の認証ヘッダー（認可テスト用）"""
    expire = datetime.utcnow() + timedelta(days=1)
    payload = {"sub": other_user.id, "exp": expire}
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_analysis(db_session, test_user):
    """テスト用分析データ"""
    analysis = Analysis(
        id="test-analysis-id",
        user_id=test_user.id,
        repo_url="https://github.com/testuser/testrepo",
        branch="main",
        scores={
            "test": 80, "comment": 70, "commit_size": 90,
            "commit_frequency": 85, "commit_message": 75, "activity": 80
        },
        report={
            "test": "Good test coverage",
            "comment": "Adequate comments",
            "commit_size": "Small, focused commits",
            "commit_frequency": "Regular commits",
            "commit_message": "Clear messages",
            "activity": "Consistent activity"
        },
    )
    db_session.add(analysis)
    db_session.commit()
    return analysis