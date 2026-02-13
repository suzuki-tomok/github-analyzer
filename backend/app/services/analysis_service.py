# app/services/analysis_service.py
import asyncio

import httpx
from sqlalchemy.orm import Session

from app.exceptions import AppException, ErrorCode
from app.logger import logger
from app.models import Analysis, User
from app.services.gemini_client import analyze_commits


async def fetch_commits_from_github(
    repo_url: str,
    branch: str,
    limit: int,
    access_token: str,
) -> str:
    """
    GitHub APIからcommit取得してテキスト形式に変換
    """
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

    async with httpx.AsyncClient() as client:

        async def fetch_detail(sha: str):
            response = await client.get(
                f"https://api.github.com/repos/{owner}/{repo}/commits/{sha}",
                headers=headers,
            )
            if response.status_code != 200:
                return None
            return response.json()

        details = await asyncio.gather(*[fetch_detail(c["sha"]) for c in commits_data])

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


async def run_analysis(
    repo_url: str,
    branch: str,
    limit: int,
    current_user: User,
    db: Session,
) -> Analysis:
    """
    GitHub取得 → Gemini分析 → DB保存 を実行
    """
    logger.info(f"Analysis | Start | user: {current_user.id} | repo: {repo_url}")

    # 1. GitHub APIからcommit取得
    parsed_log = await fetch_commits_from_github(
        repo_url, branch, limit, current_user.github_access_token
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
        repo_url=repo_url,
        branch=branch,
        scores=result["scores"],
        report=result["report"],
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    logger.info(f"Analysis | Complete | id: {analysis.id}")

    return analysis
