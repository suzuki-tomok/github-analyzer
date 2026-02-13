# app/routers/analyses.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

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
from app.services.analysis_service import run_analysis
from app.exceptions import AppException, ErrorCode, error_responses
from app.logger import logger

router = APIRouter(
    prefix="/analyses",
    tags=["analyses"],
)


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
    analysis = await run_analysis(
        request.repo_url, request.branch, request.limit, current_user, db
    )

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
