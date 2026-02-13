# app/routers/analyses.py
import asyncio

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
import httpx

from app.dependencies import get_db, get_current_user
from app.models import User, Analysis
from app.schemas import (
    AnalysisRequest,
    MemoUpdate,
    SuccessResponse,
    AnalysisResponse,
    AnalysisListItem,
    Scores,
    Report,
)
from app.services.gemini_client import analyze_commits
from app.exceptions import AppException, ErrorCode, error_responses
from app.logger import logger

router = APIRouter(
    prefix="/analyses",
    tags=["analyses"],
)


async def fetch_commits_from_github(
    repo_url: str,
    branch: str,
    limit: int,
    access_token: str,
) -> str:
    """
    GitHub APIからcommit取得してテキスト形式に変換
    """
    # repo_urlからowner/repoを抽出
    try:
        parts = repo_url.rstrip("/").split("/")
        owner = parts[-2]
        repo = parts[-1]
    except IndexError:
        raise AppException(
            400,
            ErrorCode.INVALID_REPO_URL,
            "Invalid repo_url format. Expected: https://github.com/owner/repo",
        )

    logger.debug(f"GitHub API | Fetching commits | {owner}/{repo} | branch: {branch}")

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github.v3+json",
    }

    # commit一覧取得
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.github.com/repos/{owner}/{repo}/commits",
            params={"sha": branch, "per_page": limit},
            headers=headers,
        )

    if response.status_code != 200:
        error_msg = response.json().get("message", "Unknown error")
        logger.warning(f"GitHub API | Error | {response.status_code} | {error_msg}")
        raise AppException(
            400, ErrorCode.GITHUB_API_ERROR, f"GitHub API error: {error_msg}"
        )

    commits_data = response.json()
    logger.info(f"GitHub API | Success | {len(commits_data)} commits fetched")

    # 各commitの詳細を並行取得
    async with httpx.AsyncClient() as client:

        async def fetch_detail(sha: str):
            response = await client.get(
                f"https://api.github.com/repos/{owner}/{repo}/commits/{sha}",
                headers=headers,
            )
            if response.status_code != 200:
                return None
            return response.json()

        details = await asyncio.gather(
            *[fetch_detail(c["sha"]) for c in commits_data]
        )

    lines = []
    for detail in details:
        if detail is None:
            continue

        lines.append(f"=== Commit: {detail['sha'][:7]} ===")
        lines.append(f"Author: {detail['commit']['author']['name']}")
        lines.append(f"Date: {detail['commit']['author']['date']}")
        lines.append(f"Message: {detail['commit']['message']}")
        lines.append("Files:")

        for f in detail.get("files", []):
            lines.append(
                f"  - {f.get('filename', '')} (+{f.get('additions', 0)}, -{f.get('deletions', 0)})"
            )
            patch = f.get("patch", "")
            if patch:
                lines.append(f"    Diff: {patch[:200]}...")

        lines.append("")

    return "\n".join(lines)


@router.post(
    "",
    response_model=SuccessResponse[AnalysisResponse],
    responses={
        400: error_responses[400],
        401: error_responses[401],
        500: error_responses[500],
    },
)
async def create_analysis(
    request: AnalysisRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    分析を実行してDBに保存
    """
    logger.info(
        f"Analysis | Start | user: {current_user.id} | repo: {request.repo_url}"
    )

    # 1. GitHub APIからcommit取得
    parsed_log = await fetch_commits_from_github(
        request.repo_url,
        request.branch,
        request.limit,
        current_user.github_access_token,
    )

    # 2. Geminiで分析
    logger.debug("Gemini API | Start analysis")
    try:
        result = analyze_commits(parsed_log)
        logger.info("Gemini API | Success")
    except Exception as e:
        logger.error(f"Gemini API | Error | {type(e).__name__}: {str(e)}")
        raise AppException(
            500, ErrorCode.GEMINI_API_ERROR, f"Gemini API error: {str(e)}"
        )

    # 3. DBに保存
    analysis = Analysis(
        user_id=current_user.id,
        repo_url=request.repo_url,
        branch=request.branch,
        scores=result["scores"],
        report=result["report"],
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    logger.info(f"Analysis | Complete | id: {analysis.id}")

    # 4. 結果を返す
    return SuccessResponse(
        data=AnalysisResponse(
            id=analysis.id,
            repo_url=analysis.repo_url,
            branch=analysis.branch,
            scores=Scores(**analysis.scores),
            report=Report(**analysis.report),
            memo=analysis.memo,
            created_at=analysis.created_at.isoformat(),
            updated_at=analysis.updated_at.isoformat(),
        )
    )


@router.get(
    "",
    response_model=SuccessResponse[List[AnalysisListItem]],
    responses={401: error_responses[401]},
)
def list_analyses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    ログインユーザーの分析履歴一覧を取得
    """
    analyses = (
        db.query(Analysis)
        .filter(Analysis.user_id == current_user.id)
        .order_by(Analysis.created_at.desc())
        .all()
    )

    logger.debug(f"List analyses | user: {current_user.id} | count: {len(analyses)}")

    return SuccessResponse(
        data=[
            AnalysisListItem(
                id=a.id,
                repo_url=a.repo_url,
                branch=a.branch,
                scores=Scores(**a.scores),
                memo=a.memo,
                created_at=a.created_at.isoformat(),
            )
            for a in analyses
        ]
    )


@router.get(
    "/{analysis_id}",
    response_model=SuccessResponse[AnalysisResponse],
    responses={
        401: error_responses[401],
        404: error_responses[404],
    },
)
def get_analysis(
    analysis_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    分析の詳細を取得
    """
    analysis = (
        db.query(Analysis)
        .filter(
            Analysis.id == analysis_id,
            Analysis.user_id == current_user.id,
        )
        .first()
    )

    if not analysis:
        raise AppException(404, ErrorCode.ANALYSIS_NOT_FOUND, "Analysis not found")

    return SuccessResponse(
        data=AnalysisResponse(
            id=analysis.id,
            repo_url=analysis.repo_url,
            branch=analysis.branch,
            scores=Scores(**analysis.scores),
            report=Report(**analysis.report),
            memo=analysis.memo,
            created_at=analysis.created_at.isoformat(),
            updated_at=analysis.updated_at.isoformat(),
        )
    )


@router.patch(
    "/{analysis_id}",
    responses={
        401: error_responses[401],
        404: error_responses[404],
    },
)
def update_analysis(
    analysis_id: str,
    request: MemoUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    分析のメモを更新
    """
    analysis = (
        db.query(Analysis)
        .filter(
            Analysis.id == analysis_id,
            Analysis.user_id == current_user.id,
        )
        .first()
    )

    if not analysis:
        raise AppException(404, ErrorCode.ANALYSIS_NOT_FOUND, "Analysis not found")

    analysis.memo = request.memo
    db.commit()

    logger.info(f"Update memo | id: {analysis_id}")

    return SuccessResponse(data={"message": "Updated"})


@router.delete(
    "/{analysis_id}",
    responses={
        401: error_responses[401],
        404: error_responses[404],
    },
)
def delete_analysis(
    analysis_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    分析を削除
    """
    analysis = (
        db.query(Analysis)
        .filter(
            Analysis.id == analysis_id,
            Analysis.user_id == current_user.id,
        )
        .first()
    )

    if not analysis:
        raise AppException(404, ErrorCode.ANALYSIS_NOT_FOUND, "Analysis not found")

    db.delete(analysis)
    db.commit()

    logger.info(f"Delete analysis | id: {analysis_id}")

    return SuccessResponse(data={"message": "Deleted"})