"""지표 분석 API 라우터"""

from fastapi import APIRouter, HTTPException, Query
from .service import indicator_service
from .trend_service import trend_service, stock_screener
from .analyzer import financial_analyzer, AnalysisResult, Indicator
from shared.schemas.indicators import ComprehensiveAnalysis
from shared.schemas.common import BaseResponse
from features.companies.data import COMPANIES
import asyncio

router = APIRouter()


# ========================
# 신규 분석 API (10개 지표)
# ========================

@router.get("/v2/analysis/{corp_code}")
async def get_analysis_v2(
    corp_code: str,
    corp_name: str = Query(..., description="기업명"),
    bsns_year: str = Query(..., description="사업연도 (예: 2023)"),
    fs_div: str = Query("CFS", description="재무제표 구분 (OFS: 개별, CFS: 연결)"),
):
    """
    종합 분석 v2 (10개 재무지표 기반)

    수익성: ROE, 영업이익률, 순이익률
    안정성: 부채비율, 이자보상배율, 유동비율
    성장성: 매출성장률, 영업이익성장률, 순이익성장률
    현금흐름: 현금흐름질 (버핏지표)
    """
    result = await financial_analyzer.analyze(corp_code, corp_name, bsns_year, fs_div)
    if not result:
        raise HTTPException(status_code=404, detail="재무제표 데이터를 찾을 수 없습니다.")

    from datetime import datetime

    return BaseResponse(
        success=True,
        message="분석이 완료되었습니다.",
        data={
            "corp_code": result.corp_code,
            "corp_name": result.corp_name,
            "year": result.year,
            "fs_div": fs_div,
            "total_score": result.total_score,
            "signal": result.signal,
            "recommendation": result.recommendation,
            "indicators": [
                {
                    "name": ind.name,
                    "value": ind.value,
                    "score": ind.score,
                    "grade": ind.grade,
                    "description": ind.description,
                    "good_criteria": ind.good_criteria,
                    "trend": ind.trend,
                }
                for ind in result.indicators
            ],
            "analysis_date": datetime.now().strftime("%Y-%m-%d"),
            "metrics": result.metrics,
        },
    )


@router.get("/v2/screener")
async def screener_v2(
    year: str = Query(..., description="사업연도"),
    fs_div: str = Query("CFS", description="재무제표 구분"),
    limit: int = Query(30, description="조회 개수", ge=1, le=126),
):
    """
    우량주 스크리너 v2 (10개 지표 기반)

    전체 126개 기업을 분석하여 점수순으로 정렬합니다.
    """
    results = []
    total = min(limit, len(COMPANIES))

    for i, (corp_code, corp_name, stock_code, sector) in enumerate(COMPANIES[:limit]):
        try:
            result = await financial_analyzer.analyze(corp_code, corp_name, year, fs_div)
            if result:
                results.append({
                    "rank": 0,  # 나중에 설정
                    "corp_code": corp_code,
                    "corp_name": corp_name,
                    "stock_code": stock_code,
                    "sector": sector,
                    "total_score": result.total_score,
                    "signal": result.signal,
                    "indicators": {
                        ind.name: {"value": ind.value, "grade": ind.grade}
                        for ind in result.indicators
                    },
                })
        except:
            pass

    # 점수순 정렬
    results.sort(key=lambda x: x["total_score"], reverse=True)

    # 순위 부여
    for i, r in enumerate(results, 1):
        r["rank"] = i

    return BaseResponse(
        success=True,
        message=f"{len(results)}개 기업 분석 완료",
        data={
            "total_analyzed": len(results),
            "year": year,
            "stocks": results,
        },
    )


@router.get("/analysis/{corp_code}", response_model=BaseResponse[ComprehensiveAnalysis])
async def get_analysis(
    corp_code: str,
    corp_name: str = Query(..., description="기업명"),
    bsns_year: str = Query(..., description="사업연도 (예: 2023)"),
    fs_div: str = Query("OFS", description="재무제표 구분 (OFS: 개별, CFS: 연결)"),
):
    """
    5대 지표 종합 분석

    - **corp_code**: 기업 고유번호 (8자리)
    - **corp_name**: 기업명
    - **bsns_year**: 사업연도
    - **fs_div**: 재무제표 구분
    """
    try:
        analysis = await indicator_service.get_comprehensive_analysis(
            corp_code=corp_code,
            corp_name=corp_name,
            bsns_year=bsns_year,
            fs_div=fs_div,
        )
        return BaseResponse(
            success=True,
            message="분석이 완료되었습니다.",
            data=analysis,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cash-generation/{corp_code}")
async def get_cash_generation(
    corp_code: str,
    bsns_year: str = Query(..., description="사업연도"),
    fs_div: str = Query("OFS", description="재무제표 구분"),
):
    """현금 창출 능력 지표 조회"""
    result = await indicator_service.calculate_cash_generation(corp_code, bsns_year, fs_div)
    if not result:
        raise HTTPException(status_code=404, detail="데이터를 찾을 수 없습니다.")
    return BaseResponse(success=True, message="조회 완료", data=result)


@router.get("/interest-coverage/{corp_code}")
async def get_interest_coverage(
    corp_code: str,
    bsns_year: str = Query(..., description="사업연도"),
    fs_div: str = Query("OFS", description="재무제표 구분"),
):
    """이자보상배율 지표 조회"""
    result = await indicator_service.calculate_interest_coverage(corp_code, bsns_year, fs_div)
    if not result:
        raise HTTPException(status_code=404, detail="데이터를 찾을 수 없습니다.")
    return BaseResponse(success=True, message="조회 완료", data=result)


@router.get("/operating-growth/{corp_code}")
async def get_operating_growth(
    corp_code: str,
    bsns_year: str = Query(..., description="사업연도"),
    fs_div: str = Query("OFS", description="재무제표 구분"),
):
    """영업이익 성장률 지표 조회"""
    result = await indicator_service.calculate_operating_profit_growth(corp_code, bsns_year, fs_div)
    if not result:
        raise HTTPException(status_code=404, detail="데이터를 찾을 수 없습니다.")
    return BaseResponse(success=True, message="조회 완료", data=result)


@router.get("/dilution-risk/{corp_code}")
async def get_dilution_risk(
    corp_code: str,
    bsns_year: str = Query(..., description="사업연도"),
):
    """희석 가능 물량 비율 지표 조회"""
    result = await indicator_service.calculate_dilution_risk(corp_code, bsns_year)
    if not result:
        raise HTTPException(status_code=404, detail="데이터를 찾을 수 없습니다.")
    return BaseResponse(success=True, message="조회 완료", data=result)


@router.get("/insider-trading/{corp_code}")
async def get_insider_trading(corp_code: str):
    """임원/주요주주 순매수 강도 지표 조회"""
    result = await indicator_service.calculate_insider_trading(corp_code)
    if not result:
        raise HTTPException(status_code=404, detail="데이터를 찾을 수 없습니다.")
    return BaseResponse(success=True, message="조회 완료", data=result)


@router.get("/trend/{corp_code}")
async def get_trend_analysis(
    corp_code: str,
    corp_name: str = Query(..., description="기업명"),
    bsns_year: str = Query(..., description="기준 사업연도"),
    fs_div: str = Query("OFS", description="재무제표 구분"),
):
    """
    트렌드 분석 (3개년 비교)

    영업이익, 이자보상배율, 현금흐름 품질의 추세를 분석합니다.
    """
    try:
        result = await trend_service.analyze_trend(corp_code, corp_name, bsns_year, fs_div)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return BaseResponse(success=True, message="트렌드 분석 완료", data=result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/screener/scan")
async def scan_stocks(
    year: str = Query(..., description="사업연도"),
    fs_div: str = Query("OFS", description="재무제표 구분"),
    limit: int = Query(10, description="조회 개수", ge=1, le=50),
):
    """
    우량주 스캔

    주요 기업들의 5대 지표를 분석하여 점수순으로 정렬합니다.
    """
    try:
        results = await stock_screener.scan_stocks(year, fs_div, limit)
        return BaseResponse(
            success=True,
            message=f"{len(results)}개 기업 스캔 완료",
            data=results,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/screener/top-picks")
async def get_top_picks(
    year: str = Query(..., description="사업연도"),
    fs_div: str = Query("OFS", description="재무제표 구분"),
):
    """
    추천 종목 조회

    종합 점수 70점 이상인 우량 종목을 반환합니다.
    """
    try:
        results = await stock_screener.get_top_picks(year, fs_div)
        return BaseResponse(
            success=True,
            message=f"{len(results)}개 추천 종목 조회",
            data=results,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
