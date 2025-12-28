"""기업 검색 API 라우터"""

from fastapi import APIRouter, Query
from shared.schemas.common import BaseResponse
from .data import search_companies, get_all_companies

router = APIRouter()


@router.get("/search")
async def search(
    q: str = Query(..., description="검색어 (기업명 또는 종목코드)", min_length=1),
    limit: int = Query(10, description="최대 결과 수", ge=1, le=50),
):
    """
    기업 검색

    기업명 또는 종목코드로 검색합니다.
    """
    results = search_companies(q, limit)
    return BaseResponse(
        success=True,
        message=f"{len(results)}개 기업 검색됨",
        data=results,
    )


@router.get("/list")
async def list_companies(
    sector: str | None = Query(None, description="업종 필터"),
):
    """
    전체 기업 목록

    분석 가능한 전체 기업 목록을 반환합니다.
    """
    companies = get_all_companies()

    if sector:
        companies = [c for c in companies if c["sector"] == sector]

    return BaseResponse(
        success=True,
        message=f"{len(companies)}개 기업",
        data=companies,
    )


@router.get("/sectors")
async def get_sectors():
    """
    업종 목록

    분석 가능한 업종 목록을 반환합니다.
    """
    companies = get_all_companies()
    sectors = sorted(set(c["sector"] for c in companies))

    return BaseResponse(
        success=True,
        message=f"{len(sectors)}개 업종",
        data=sectors,
    )
