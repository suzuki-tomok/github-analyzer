# tests/routers/test_auth.py
"""
/auth エンドポイントのテスト
"""
from jose import jwt
from datetime import datetime, timedelta
from app.config import settings


class TestGetAuthMe:
    """
    GET /auth/me
    現在ログイン中のユーザー情報を取得
    """
    
    def test_success(self, client, auth_header, test_user):
        """正常系：認証済みユーザー情報取得"""
        response = client.get("/auth/me", headers=auth_header)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["github_username"] == test_user.github_username
    
    def test_no_token_401(self, client):
        """異常系：トークンなし"""
        response = client.get("/auth/me")
        
        assert response.status_code == 401
    
    def test_invalid_token_401(self, client):
        """異常系：不正なトークン"""
        response = client.get(
            "/auth/me",
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        assert response.status_code == 401
        assert response.json()["code"] == "INVALID_TOKEN"
    
    def test_expired_token_401(self, client, test_user):
        """異常系：期限切れトークン"""
        expire = datetime.utcnow() - timedelta(days=1)
        payload = {"sub": test_user.id, "exp": expire}
        token = jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")
        
        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 401