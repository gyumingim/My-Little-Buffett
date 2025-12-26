"""지표 분석 API 라우터 - 버핏형 가치투자 분석"""

from datetime import datetime
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from .service import indicator_service
from .trend_service import trend_service, stock_screener
from .analyzer import financial_analyzer
from shared.schemas.indicators import ComprehensiveAnalysis
from shared.schemas.common import BaseResponse
from shared.cache.sqlite_cache import (
    save_buffett_analysis,
    get_buffett_analysis,
    get_buffett_analysis_count,
    get_available_years,
    clear_buffett_analysis,
)
from features.companies.data import COMPANIES

router = APIRouter()


# ========================
# 버핏형 분석 API v2
# ========================

@router.get("/v2/analysis/{corp_code}")
async def get_analysis_v2(
    corp_code: str,
    corp_name: str = Query(..., description="기업명"),
    bsns_year: str = Query(..., description="사업연도 (예: 2023)"),
    fs_div: str = Query("CFS", description="재무제표 구분 (OFS: 개별, CFS: 연결)"),
):
    """
    버핏형 종합 분석 (100점 만점)

    채점 기준:
    - ROE (30점): 15% 이상 지속
    - 현금창출력 (25점): OCF/NI >= 1.2
    - 영업이익 성장률 (20점): 15% 이상
    - 이자보상배율 (15점): 3배 이상
    - 부채비율 (10점): 100% 이하

    필터링:
    - 이자보상배율 < 1.0 → 부적격
    - 2년 연속 영업CF < 순이익 → 부적격
    - 자본잠식 → 부적격
    - 2년 연속 적자 → 부적격
    """
    result = await financial_analyzer.analyze(corp_code, corp_name, bsns_year, fs_div)
    if not result:
        raise HTTPException(status_code=404, detail="재무제표 데이터를 찾을 수 없습니다.")

    return BaseResponse(
        success=True,
        message="분석이 완료되었습니다.",
        data={
            "corp_code": result.corp_code,
            "corp_name": result.corp_name,
            "year": result.year,
            "fs_div": result.fs_div,
            "total_score": result.total_score,
            "signal": result.signal,
            "recommendation": result.recommendation,
            "filter_passed": result.filter_result.passed,
            "filter_reasons": result.filter_result.failed_reasons,
            "indicators": [
                {
                    "name": ind.name,
                    "value": ind.value,
                    "score": ind.score,
                    "max_score": ind.max_score,
                    "grade": ind.grade,
                    "description": ind.description,
                    "good_criteria": ind.good_criteria,
                    "category": ind.category,
                }
                for ind in result.indicators
            ],
            "analysis_date": datetime.now().strftime("%Y-%m-%d"),
        },
    )


@router.get("/v2/screener")
async def screener_v2(
    year: str = Query(..., description="사업연도"),
    fs_div: str = Query("CFS", description="재무제표 구분"),
    limit: int = Query(100, description="조회 개수", ge=1, le=4000),
    use_cache: bool = Query(True, description="저장된 분석 결과 사용"),
):
    """
    버핏형 우량주 스크리너

    전체 기업을 버핏 기준으로 분석하여 점수순 정렬.
    필터링 탈락 기업은 별도 표시.
    분석 결과는 DB에 영구 저장됨.
    """
    # 캐시된 결과가 있으면 사용
    if use_cache:
        cached_count = get_buffett_analysis_count(year, fs_div)
        if cached_count > 0:
            cached = get_buffett_analysis(year, fs_div)
            results = [r for r in cached if r["filter_passed"]][:limit]
            filtered_out = [r for r in cached if not r["filter_passed"]][:20]

            # 순위 부여
            for i, r in enumerate(results, 1):
                r["rank"] = i

            return BaseResponse(
                success=True,
                message=f"[DB] {len(results)}개 우량주 / {len(filtered_out)}개 필터링 탈락 (저장된 {cached_count}개 중)",
                data={
                    "year": year,
                    "total_analyzed": cached_count,
                    "passed_count": len([r for r in cached if r["filter_passed"]]),
                    "filtered_count": len([r for r in cached if not r["filter_passed"]]),
                    "no_data_count": 0,
                    "from_cache": True,
                    "stocks": results,
                    "filtered_out": filtered_out,
                    "no_data_corps": [],
                },
            )

    # 새로 분석
    results = []
    filtered_out = []
    no_data_corps = []

    for corp_code, corp_name, stock_code, sector in COMPANIES[:limit]:
        try:
            result = await financial_analyzer.analyze(corp_code, corp_name, year, fs_div)
            if result:
                indicators_dict = {
                    ind.name: {
                        "value": ind.value,
                        "score": ind.score,
                        "max_score": ind.max_score,
                        "grade": ind.grade,
                    }
                    for ind in result.indicators
                }

                # DB에 저장
                save_buffett_analysis(
                    corp_code=corp_code,
                    corp_name=corp_name,
                    stock_code=stock_code,
                    sector=sector,
                    bsns_year=year,
                    fs_div=fs_div,
                    total_score=result.total_score,
                    signal=result.signal,
                    filter_passed=result.filter_result.passed,
                    filter_reasons=result.filter_result.failed_reasons,
                    indicators=indicators_dict,
                )

                item = {
                    "corp_code": corp_code,
                    "corp_name": corp_name,
                    "stock_code": stock_code,
                    "sector": sector,
                    "total_score": result.total_score,
                    "signal": result.signal,
                    "filter_passed": result.filter_result.passed,
                    "filter_reasons": result.filter_result.failed_reasons,
                    "indicators": indicators_dict,
                }
                if result.filter_result.passed:
                    results.append(item)
                else:
                    filtered_out.append(item)
            else:
                no_data_corps.append(corp_name)
        except Exception as e:
            no_data_corps.append(f"{corp_name}(오류: {str(e)[:30]})")

    # 점수순 정렬
    results.sort(key=lambda x: x["total_score"], reverse=True)
    filtered_out.sort(key=lambda x: x["total_score"], reverse=True)

    # 순위 부여
    for i, r in enumerate(results, 1):
        r["rank"] = i

    return BaseResponse(
        success=True,
        message=f"{len(results)}개 우량주 / {len(filtered_out)}개 필터링 탈락 / {len(no_data_corps)}개 데이터 없음",
        data={
            "year": year,
            "total_analyzed": len(results) + len(filtered_out),
            "passed_count": len(results),
            "filtered_count": len(filtered_out),
            "no_data_count": len(no_data_corps),
            "from_cache": False,
            "stocks": results,
            "filtered_out": filtered_out[:20],
            "no_data_corps": no_data_corps[:30],
        },
    )


@router.get("/v2/screener/years")
async def get_screener_years():
    """저장된 분석 연도 목록 조회"""
    years = get_available_years()
    return BaseResponse(
        success=True,
        message=f"{len(years)}개 연도 데이터 있음",
        data={"years": years}
    )


@router.post("/v2/screener/refresh")
async def refresh_screener(
    year: str = Query(..., description="사업연도"),
    fs_div: str = Query("CFS", description="재무제표 구분"),
    limit: int = Query(100, description="분석 개수", ge=1, le=4000),
):
    """
    스크리너 데이터 새로고침 (기존 캐시 삭제 후 재분석)
    """
    # 해당 연도/재무제표 캐시 삭제
    clear_buffett_analysis(year, fs_div)

    # 새로 분석 (use_cache=False로 호출)
    results = []
    filtered_out = []
    no_data_corps = []
    saved_count = 0

    for corp_code, corp_name, stock_code, sector in COMPANIES[:limit]:
        try:
            result = await financial_analyzer.analyze(corp_code, corp_name, year, fs_div)
            if result:
                indicators_dict = {
                    ind.name: {
                        "value": ind.value,
                        "score": ind.score,
                        "max_score": ind.max_score,
                        "grade": ind.grade,
                    }
                    for ind in result.indicators
                }

                # DB에 저장
                save_buffett_analysis(
                    corp_code=corp_code,
                    corp_name=corp_name,
                    stock_code=stock_code,
                    sector=sector,
                    bsns_year=year,
                    fs_div=fs_div,
                    total_score=result.total_score,
                    signal=result.signal,
                    filter_passed=result.filter_result.passed,
                    filter_reasons=result.filter_result.failed_reasons,
                    indicators=indicators_dict,
                )
                saved_count += 1

                if result.filter_result.passed:
                    results.append(corp_name)
                else:
                    filtered_out.append(corp_name)
            else:
                no_data_corps.append(corp_name)
        except Exception as e:
            no_data_corps.append(f"{corp_name}(오류)")

    return BaseResponse(
        success=True,
        message=f"{saved_count}개 기업 분석 완료 및 DB 저장",
        data={
            "year": year,
            "fs_div": fs_div,
            "saved_count": saved_count,
            "passed_count": len(results),
            "filtered_count": len(filtered_out),
            "no_data_count": len(no_data_corps),
        },
    )


# ========================
# 기존 API (하위 호환)
# ========================

@router.get("/analysis/{corp_code}", response_model=BaseResponse[ComprehensiveAnalysis])
async def get_analysis(
    corp_code: str,
    corp_name: str = Query(..., description="기업명"),
    bsns_year: str = Query(..., description="사업연도 (예: 2023)"),
    fs_div: str = Query("OFS", description="재무제표 구분 (OFS: 개별, CFS: 연결)"),
):
    """
    5대 지표 종합 분석 (레거시)
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
    """트렌드 분석 (3개년 비교)"""
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
    """우량주 스캔 (레거시)"""
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
    """추천 종목 조회 (레거시)"""
    try:
        results = await stock_screener.get_top_picks(year, fs_div)
        return BaseResponse(
            success=True,
            message=f"{len(results)}개 추천 종목 조회",
            data=results,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
