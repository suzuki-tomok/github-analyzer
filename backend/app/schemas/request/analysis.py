# app/schemas/request/analysis.py
from pydantic import BaseModel, Field, field_validator
import re


class AnalysisRequest(BaseModel):
    repo_url: str = Field(..., min_length=1, examples=["https://github.com/user/repo"])
    branch: str = Field(default="main", min_length=1, max_length=255)
    limit: int = Field(default=30, ge=1, le=30)

    @field_validator("repo_url")
    @classmethod
    def validate_github_url(cls, v: str) -> str:
        """GitHub URL形式チェック（インジェクション対策）"""
        pattern = r"^https://github\.com/[\w\-\.]+/[\w\-\.]+/?$"
        if not re.match(pattern, v):
            raise ValueError("Invalid GitHub URL format")
        return v.rstrip("/")

    @field_validator("branch")
    @classmethod
    def sanitize_branch(cls, v: str) -> str:
        """ブランチ名サニタイズ（コマンドインジェクション対策）"""
        if re.search(r"[;&|`$\\'\"\n\r]", v):
            raise ValueError("Invalid branch name")
        return v


class MemoUpdate(BaseModel):
    memo: str = Field(..., max_length=1000)
