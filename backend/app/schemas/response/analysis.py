# app/schemas/response/analysis.py
from pydantic import BaseModel
from typing import Optional


class Scores(BaseModel):
    test: int
    comment: int
    commit_size: int
    commit_frequency: int
    commit_message: int
    activity: int


class Report(BaseModel):
    test: str
    comment: str
    commit_size: str
    commit_frequency: str
    commit_message: str
    activity: str


class AnalysisData(BaseModel):
    scores: Scores
    report: Report


class AnalysisResponse(BaseModel):
    id: str
    repo_url: str
    branch: str
    scores: Scores
    report: Report
    memo: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None


class AnalysisListItem(BaseModel):
    id: str
    repo_url: str
    branch: str
    scores: Scores
    memo: Optional[str] = None
    created_at: str
