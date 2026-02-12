# tests/routers/test_analyses.py
"""
/analyses エンドポイントのテスト
"""
from unittest.mock import patch


class TestGetAnalyses:
    """
    GET /analyses
    分析履歴一覧を取得
    """
    
    def test_success_with_data(self, client, auth_header, test_analysis):
        """正常系：データあり"""
        response = client.get("/analyses", headers=auth_header)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert len(data["data"]) == 1
        assert data["data"][0]["repo_url"] == test_analysis.repo_url
    
    def test_success_empty(self, client, auth_header):
        """正常系：データなし"""
        response = client.get("/analyses", headers=auth_header)
        
        assert response.status_code == 200
        assert response.json()["data"] == []
    
    def test_no_token_401(self, client):
        """異常系：未認証"""
        response = client.get("/analyses")
        
        assert response.status_code == 401


class TestGetAnalysisDetail:
    """
    GET /analyses/{id}
    分析詳細を取得
    """
    
    def test_success(self, client, auth_header, test_analysis):
        """正常系：詳細取得"""
        response = client.get(
            f"/analyses/{test_analysis.id}",
            headers=auth_header
        )
        
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["id"] == test_analysis.id
        assert data["scores"]["test"] == 80
    
    def test_not_found_404(self, client, auth_header):
        """異常系：存在しないID"""
        response = client.get(
            "/analyses/nonexistent-id",
            headers=auth_header
        )
        
        assert response.status_code == 404
        assert response.json()["code"] == "ANALYSIS_NOT_FOUND"
    
    def test_other_user_404(self, client, other_auth_header, test_analysis):
        """異常系：他人のデータにアクセス"""
        response = client.get(
            f"/analyses/{test_analysis.id}",
            headers=other_auth_header
        )
        
        assert response.status_code == 404
    
    def test_no_token_401(self, client, test_analysis):
        """異常系：未認証"""
        response = client.get(f"/analyses/{test_analysis.id}")
        
        assert response.status_code == 401


class TestUpdateAnalysis:
    """
    PATCH /analyses/{id}
    分析のメモを更新
    """
    
    def test_success(self, client, auth_header, test_analysis):
        """正常系：メモ更新"""
        response = client.patch(
            f"/analyses/{test_analysis.id}",
            headers=auth_header,
            json={"memo": "Updated memo"}
        )
        
        assert response.status_code == 200
    
    def test_not_found_404(self, client, auth_header):
        """異常系：存在しないID"""
        response = client.patch(
            "/analyses/nonexistent-id",
            headers=auth_header,
            json={"memo": "test"}
        )
        
        assert response.status_code == 404
    
    def test_other_user_404(self, client, other_auth_header, test_analysis):
        """異常系：他人のデータを更新"""
        response = client.patch(
            f"/analyses/{test_analysis.id}",
            headers=other_auth_header,
            json={"memo": "hacked"}
        )
        
        assert response.status_code == 404
    
    def test_memo_too_long_422(self, client, auth_header, test_analysis):
        """異常系：メモが1001文字（境界値）"""
        response = client.patch(
            f"/analyses/{test_analysis.id}",
            headers=auth_header,
            json={"memo": "x" * 1001}
        )
        
        assert response.status_code == 422
    
    def test_memo_max_length_success(self, client, auth_header, test_analysis):
        """正常系：メモが1000文字（境界値）"""
        response = client.patch(
            f"/analyses/{test_analysis.id}",
            headers=auth_header,
            json={"memo": "x" * 1000}
        )
        
        assert response.status_code == 200
    
    def test_no_token_401(self, client, test_analysis):
        """異常系：未認証"""
        response = client.patch(
            f"/analyses/{test_analysis.id}",
            json={"memo": "test"}
        )
        
        assert response.status_code == 401


class TestDeleteAnalysis:
    """
    DELETE /analyses/{id}
    分析を削除
    """
    
    def test_success(self, client, auth_header, test_analysis, db_session):
        """正常系：削除"""
        response = client.delete(
            f"/analyses/{test_analysis.id}",
            headers=auth_header
        )
        
        assert response.status_code == 200
        
        # DBから消えていることを確認
        from app.models import Analysis
        deleted = db_session.query(Analysis).filter(
            Analysis.id == test_analysis.id
        ).first()
        assert deleted is None
    
    def test_not_found_404(self, client, auth_header):
        """異常系：存在しないID"""
        response = client.delete(
            "/analyses/nonexistent-id",
            headers=auth_header
        )
        
        assert response.status_code == 404
    
    def test_other_user_404(self, client, other_auth_header, test_analysis):
        """異常系：他人のデータを削除"""
        response = client.delete(
            f"/analyses/{test_analysis.id}",
            headers=other_auth_header
        )
        
        assert response.status_code == 404
    
    def test_no_token_401(self, client, test_analysis):
        """異常系：未認証"""
        response = client.delete(f"/analyses/{test_analysis.id}")
        
        assert response.status_code == 401


class TestCreateAnalysis:
    """
    POST /analyses
    分析を実行
    """
    
    @patch("app.routers.analyses.fetch_commits_from_github")
    @patch("app.routers.analyses.analyze_commits")
    def test_success(self, mock_gemini, mock_github, client, auth_header):
        """正常系：分析作成（モック）"""
        mock_github.return_value = "=== Commit: abc1234 ===\nMessage: test"
        mock_gemini.return_value = {
            "scores": {
                "test": 80, "comment": 70, "commit_size": 90,
                "commit_frequency": 85, "commit_message": 75, "activity": 80
            },
            "report": {
                "test": "Good", "comment": "OK", "commit_size": "Small",
                "commit_frequency": "Regular", "commit_message": "Clear",
                "activity": "Active"
            }
        }
        
        response = client.post(
            "/analyses",
            headers=auth_header,
            json={
                "repo_url": "https://github.com/testuser/testrepo",
                "branch": "main",
                "limit": 10
            }
        )
        
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["scores"]["test"] == 80
    
    def test_invalid_repo_url_422(self, client, auth_header):
        """異常系：不正なrepo_url"""
        response = client.post(
            "/analyses",
            headers=auth_header,
            json={
                "repo_url": "https://gitlab.com/user/repo",
                "branch": "main"
            }
        )
        
        assert response.status_code == 422
    
    def test_limit_boundary_min_success(self, client, auth_header):
        """正常系：limit=1（境界値）"""
        with patch("app.routers.analyses.fetch_commits_from_github") as mock_gh, \
             patch("app.routers.analyses.analyze_commits") as mock_gem:
            mock_gh.return_value = "commit"
            mock_gem.return_value = {
                "scores": {"test": 80, "comment": 70, "commit_size": 90,
                          "commit_frequency": 85, "commit_message": 75, "activity": 80},
                "report": {"test": "G", "comment": "G", "commit_size": "G",
                          "commit_frequency": "G", "commit_message": "G", "activity": "G"}
            }
            
            response = client.post(
                "/analyses",
                headers=auth_header,
                json={
                    "repo_url": "https://github.com/user/repo",
                    "branch": "main",
                    "limit": 1
                }
            )
            
            assert response.status_code == 200
    
    def test_limit_boundary_over_422(self, client, auth_header):
        """異常系：limit=31（境界値）"""
        response = client.post(
            "/analyses",
            headers=auth_header,
            json={
                "repo_url": "https://github.com/user/repo",
                "branch": "main",
                "limit": 31
            }
        )
        
        assert response.status_code == 422
    
    def test_no_token_401(self, client):
        """異常系：未認証"""
        response = client.post(
            "/analyses",
            json={
                "repo_url": "https://github.com/user/repo",
                "branch": "main"
            }
        )
        
        assert response.status_code == 401