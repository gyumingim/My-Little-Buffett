"""기업 검색 및 비교 API 라우터"""

from fastapi import APIRouter, Query
from shared.schemas.common import BaseResponse
from .data import search_companies, get_company_by_code, get_all_companies
from features.indicators.service import indicator_service

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


@router.get("/compare")
async def compare_companies(
    corp_code_1: str = Query(..., description="첫 번째 기업 고유번호"),
    corp_code_2: str = Query(..., description="두 번째 기업 고유번호"),
    bsns_year: str = Query(..., description="사업연도"),
    fs_div: str = Query("OFS", description="재무제표 구분"),
):
    """
    기업 비교 분석

    두 기업의 5대 지표를 비교합니다.
    """
    company1 = get_company_by_code(corp_code_1)
    company2 = get_company_by_code(corp_code_2)

    if not company1 or not company2:
        return BaseResponse(
            success=False,
            message="기업을 찾을 수 없습니다.",
            data=None,
        )

    try:
        analysis1 = await indicator_service.get_comprehensive_analysis(
            corp_code=corp_code_1,
            corp_name=company1["corp_name"],
            bsns_year=bsns_year,
            fs_div=fs_div,
        )

        analysis2 = await indicator_service.get_comprehensive_analysis(
            corp_code=corp_code_2,
            corp_name=company2["corp_name"],
            bsns_year=bsns_year,
            fs_div=fs_div,
        )

        # 비교 결과 생성
        comparison = {
            "company1": {
                "info": company1,
                "analysis": analysis1.model_dump() if analysis1 else None,
            },
            "company2": {
                "info": company2,
                "analysis": analysis2.model_dump() if analysis2 else None,
            },
            "comparison": {
                "score_diff": (analysis1.overall_score if analysis1 else 0)
                - (analysis2.overall_score if analysis2 else 0),
                "winner": company1["corp_name"]
                if (analysis1 and analysis2 and analysis1.overall_score > analysis2.overall_score)
                else company2["corp_name"]
                if (analysis1 and analysis2 and analysis2.overall_score > analysis1.overall_score)
                else "동점",
            },
        }

        return BaseResponse(
            success=True,
            message="비교 분석 완료",
            data=comparison,
        )

    except Exception as e:
        return BaseResponse(
            success=False,
            message=str(e),
            data=None,
        )
