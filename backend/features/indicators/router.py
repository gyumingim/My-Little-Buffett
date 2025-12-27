"""지표 분석 API 라우터 - 버핏형 가치투자 분석

API 호출과 분석이 완전히 분리됨:
1. /fetch - DART API 호출해서 CSV 저장만
2. /analyze - CSV 읽어서 점수 계산만
"""

import asyncio
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from .service import indicator_service
from .trend_service import trend_service, stock_screener
from .analyzer import financial_analyzer
from shared.schemas.indicators import ComprehensiveAnalysis
from shared.schemas.common import BaseResponse
from shared.cache import (
    save_buffett_analysis,
    get_buffett_analysis,
    get_buffett_analysis_count,
    get_available_years,
    clear_buffett_analysis,
)
from shared.storage.csv_storage import csv_storage
from shared.api.dart_client import dart_client
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

    # COMPANIES 전체 사용 (limit이 전체보다 크면 전체 사용)
    companies_to_analyze = COMPANIES if limit >= len(COMPANIES) else COMPANIES[:limit]

    # 병렬 처리 함수
    async def analyze_company(corp_code, corp_name, stock_code, sector):
        try:
            # === 1단계: 쓰레기 데이터 분리수거 (Gemini 필터) ===
            from features.companies.filter import is_trash_stock
            is_trash, trash_reason = is_trash_stock(corp_name, stock_code)
            if is_trash:
                # 쓰레기 주식은 DB에 저장하되, 필터 탈락으로 표시
                save_buffett_analysis(
                    corp_code=corp_code,
                    corp_name=corp_name,
                    stock_code=stock_code,
                    sector=sector,
                    bsns_year=year,
                    fs_div=fs_div,
                    total_score=0,
                    signal="투자금지",
                    filter_passed=False,
                    filter_reasons=[f"쓰레기주식: {trash_reason}"],
                    indicators={},
                    data_source="1단계 필터 탈락",
                )
                return {
                    "corp_code": corp_code,
                    "corp_name": corp_name,
                    "stock_code": stock_code,
                    "sector": sector,
                    "total_score": 0,
                    "signal": "투자금지",
                    "filter_passed": False,
                    "filter_reasons": [f"쓰레기주식: {trash_reason}"],
                    "indicators": {},
                }

            # === 2단계: 재무제표 분석 ===
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
                    data_source=result.data_source,
                )

                return {
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
            else:
                # 데이터 없는 기업도 DB에 저장 (리스트에 표시되도록)
                save_buffett_analysis(
                    corp_code=corp_code,
                    corp_name=corp_name,
                    stock_code=stock_code,
                    sector=sector,
                    bsns_year=year,
                    fs_div=fs_div,
                    total_score=0,
                    signal="데이터없음",
                    filter_passed=False,
                    filter_reasons=["재무제표 데이터 없음"],
                    indicators={},
                    data_source="데이터 없음",
                )
                print(f"[SCREENER] {corp_name}: No data available (saved to DB)")
                return {
                    "corp_code": corp_code,
                    "corp_name": corp_name,
                    "stock_code": stock_code,
                    "sector": sector,
                    "total_score": 0,
                    "signal": "데이터없음",
                    "filter_passed": False,
                    "filter_reasons": ["재무제표 데이터 없음"],
                    "indicators": {},
                    "no_data": True,
                }
        except Exception as e:
            print(f"[SCREENER ERROR] {corp_name}: {e}")
            return {"error": f"{corp_name}(오류: {str(e)[:30]})"}

    # 배치 단위로 병렬 처리 (50개씩 - 안정성과 속도 균형)
    batch_size = 50
    for i in range(0, len(companies_to_analyze), batch_size):
        batch = companies_to_analyze[i:i+batch_size]
        tasks = [analyze_company(code, name, stock, sector) for code, name, stock, sector in batch]
        batch_results = await asyncio.gather(*tasks)

        # 배치 간 대기 제거 (속도 최우선)
        # await asyncio.sleep(0)  # 딜레이 없음

        for item in batch_results:
            if "error" in item:
                no_data_corps.append(item["error"])
            elif item.get("no_data"):
                # 데이터 없는 기업도 filtered_out에 포함 (UI에 표시)
                filtered_out.append(item)
                no_data_corps.append(item["corp_name"])
            elif item.get("filter_passed"):
                results.append(item)
            else:
                filtered_out.append(item)

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
    limit: int = Query(100, description="분석 개수", ge=1, le=5000),
):
    """
    스크리너 데이터 새로고침 (CSV 없는 기업만 API 호출, 병렬 처리)
    """
    import time
    start_time = time.time()

    print(f"[REFRESH] Starting analysis for {year}/{fs_div}, limit={limit}")

    # 전체 COMPANIES 사용 (limit이 전체보다 크면 전체 사용)
    all_companies = COMPANIES[:limit] if limit < len(COMPANIES) else COMPANIES

    # CSV 존재하는 기업과 없는 기업 구분
    from shared.storage.csv_storage import csv_storage
    companies_to_analyze = []
    companies_skipped = []

    for corp_code, corp_name, stock_code, sector in all_companies:
        # CSV 파일 존재 확인
        params = {
            "corp_code": corp_code,
            "bsns_year": year,
            "reprt_code": "11011",  # 사업보고서
            "fs_div": fs_div
        }

        if csv_storage.file_exists("fnlttSinglAcntAll.json", params):
            companies_skipped.append(corp_name)
        else:
            companies_to_analyze.append((corp_code, corp_name, stock_code, sector))

    total = len(companies_to_analyze)
    print(f"[REFRESH] Skipped {len(companies_skipped)} companies (CSV exists)")
    print(f"[REFRESH] Fetching {total} companies (CSV missing)")

    # 새로 분석 (병렬 처리)
    results = []
    filtered_out = []
    no_data_corps = []
    error_corps = []
    saved_count = 0

    # 병렬 처리 함수
    async def analyze_and_save(corp_code, corp_name, stock_code, sector):
        try:
            # === 1단계: 쓰레기 데이터 분리수거 (Gemini 필터) ===
            from features.companies.filter import is_trash_stock
            is_trash, trash_reason = is_trash_stock(corp_name, stock_code)
            if is_trash:
                save_buffett_analysis(
                    corp_code=corp_code,
                    corp_name=corp_name,
                    stock_code=stock_code,
                    sector=sector,
                    bsns_year=year,
                    fs_div=fs_div,
                    total_score=0,
                    signal="투자금지",
                    filter_passed=False,
                    filter_reasons=[f"쓰레기주식: {trash_reason}"],
                    indicators={},
                    data_source="1단계 필터 탈락",
                )
                return {"saved": True, "passed": False, "corp_name": corp_name, "trash": True}

            # === 2단계: 재무제표 분석 ===
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
                    data_source=result.data_source,
                )
                return {"saved": True, "passed": result.filter_result.passed, "corp_name": corp_name}
            else:
                # 데이터 없는 기업도 DB에 저장 (리스트에 표시되도록)
                save_buffett_analysis(
                    corp_code=corp_code,
                    corp_name=corp_name,
                    stock_code=stock_code,
                    sector=sector,
                    bsns_year=year,
                    fs_div=fs_div,
                    total_score=0,
                    signal="데이터없음",
                    filter_passed=False,
                    filter_reasons=["재무제표 데이터 없음"],
                    indicators={},
                    data_source="데이터 없음",
                )
                return {"saved": True, "passed": False, "corp_name": corp_name, "no_data": True}
        except Exception as e:
            print(f"[REFRESH ERROR] {corp_name}: {e}")
            return {"error": f"{corp_name}({str(e)[:50]})"}

    # 배치 단위로 병렬 처리 (50개씩 - 안정성과 속도 균형)
    batch_size = 50
    for i in range(0, total, batch_size):
        batch = companies_to_analyze[i:i+batch_size]
        tasks = [analyze_and_save(code, name, stock, sector) for code, name, stock, sector in batch]
        batch_results = await asyncio.gather(*tasks)

        for item in batch_results:
            if "saved" in item:
                saved_count += 1
                if item["passed"]:
                    results.append(item["corp_name"])
                else:
                    filtered_out.append(item["corp_name"])
                    if item.get("no_data"):
                        no_data_corps.append(item["corp_name"])
            elif "error" in item:
                error_corps.append(item["error"])

        # 진행 상황 로깅
        elapsed = time.time() - start_time
        print(f"[REFRESH] Progress: {min(i+batch_size, total)}/{total} ({elapsed:.1f}s) - saved={saved_count}, no_data={len(no_data_corps)}")

        # 배치 간 대기 제거 (속도 최우선)
        # await asyncio.sleep(0)  # 딜레이 없음

    elapsed = time.time() - start_time
    print(f"[REFRESH] Complete: {saved_count} saved, {len(no_data_corps)} no_data, {len(error_corps)} errors in {elapsed:.1f}s")

    return BaseResponse(
        success=True,
        message=f"{saved_count}개 기업 분석 완료 및 DB 저장 ({elapsed:.1f}초)",
        data={
            "year": year,
            "fs_div": fs_div,
            "saved_count": saved_count,
            "passed_count": len(results),
            "filtered_count": len(filtered_out),
            "no_data_count": len(no_data_corps),
            "error_count": len(error_corps),
            "elapsed_seconds": round(elapsed, 1),
            "no_data_corps": no_data_corps[:30],  # 처음 30개만
            "error_corps": error_corps[:10],  # 처음 10개만
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


# ========================
# 디버그 API
# ========================

@router.get("/v2/debug/cache-status/{corp_code}")
async def debug_cache_status(
    corp_code: str,
    bsns_year: str = Query(..., description="사업연도"),
):
    """
    디버깅용: 특정 기업의 API 캐시 상태 확인
    CFS/OFS 모두 확인하여 어떤 데이터가 캐시되어 있는지 표시
    """
    from shared.cache import get_stored

    results = {}

    # 4년치 × 2종류(CFS, OFS) 확인
    for fs_div in ["CFS", "OFS"]:
        for year_offset in range(4):
            check_year = str(int(bsns_year) - year_offset)
            params = {
                "corp_code": corp_code,
                "bsns_year": check_year,
                "reprt_code": "11011",
                "fs_div": fs_div,
            }

            cached = get_stored("fnlttSinglAcntAll.json", params)

            key = f"{fs_div}/{check_year}"
            if cached:
                status = cached.get("status", "unknown")
                msg = cached.get("message", "")
                has_data = "list" in cached and len(cached.get("list", [])) > 0
                item_count = len(cached.get("list", [])) if has_data else 0
                results[key] = {
                    "cached": True,
                    "status": status,
                    "message": msg[:50] if msg else None,
                    "has_data": has_data,
                    "item_count": item_count,
                }
            else:
                results[key] = {"cached": False}

    # 사용 가능한 데이터 요약
    available = [k for k, v in results.items() if v.get("has_data")]

    return BaseResponse(
        success=True,
        message=f"캐시 상태: {len(available)}개 조합에 데이터 있음",
        data={
            "corp_code": corp_code,
            "base_year": bsns_year,
            "cache_status": results,
            "available_combinations": available,
        }
    )


@router.get("/v2/debug/{corp_code}")
async def debug_analysis(
    corp_code: str,
    bsns_year: str = Query(..., description="사업연도"),
    fs_div: str = Query("CFS", description="재무제표 구분"),
):
    """
    디버깅용: DART API 원본 응답과 파싱 결과 확인
    """
    from shared.api.dart_client import dart_client
    from .analyzer import extract_metrics, extract_metrics_with_fallback

    # DART API 호출
    data = await dart_client.get_financial_statements(
        corp_code=corp_code, bsns_year=bsns_year, reprt_code="11011", fs_div=fs_div
    )

    if data.get("status") != "000":
        return BaseResponse(
            success=False,
            message=f"DART API 오류: {data.get('message')}",
            data={"status": data.get("status"), "message": data.get("message")}
        )

    statements = data.get("list", [])

    # 주요 항목 추출 (IS, BS, CF)
    key_items = []
    is_items = []  # 손익계산서 전체 항목 (디버깅용)

    for item in statements:
        sj_div = item.get("sj_div", "")
        account_nm = item.get("account_nm", "")
        account_id = item.get("account_id", "")
        thstrm = item.get("thstrm_amount", "")

        # 손익계산서 전체 (상위 20개)
        if sj_div == "IS" and len(is_items) < 20:
            is_items.append({"name": account_nm, "id": account_id, "amount": thstrm})

        # 주요 항목만 필터
        if sj_div == "IS" and any(kw in account_nm for kw in ["매출", "영업", "순이익", "손익", "이익"]):
            key_items.append({"type": "IS", "name": account_nm, "amount": thstrm})
        elif sj_div == "BS" and any(kw in account_nm for kw in ["자산총계", "부채총계", "자본총계", "자본과부채"]):
            key_items.append({"type": "BS", "name": account_nm, "amount": thstrm})
        elif sj_div == "CF" and any(kw in account_nm for kw in ["영업활동", "투자활동", "재무활동"]):
            key_items.append({"type": "CF", "name": account_nm, "amount": thstrm})

    # 파싱 결과 (fallback 적용)
    metrics = extract_metrics_with_fallback(statements)
    metrics_raw = extract_metrics(statements, "thstrm")  # fallback 없는 원본

    # ROE 계산
    roe = (metrics.net_income / metrics.total_equity * 100) if metrics.total_equity > 0 else 0
    debt_ratio = (metrics.total_liabilities / metrics.total_equity * 100) if metrics.total_equity > 0 else 0

    # fallback 적용 여부 확인
    fallback_applied = {
        "net_income": metrics.net_income != metrics_raw.net_income,
        "total_equity": metrics.total_equity != metrics_raw.total_equity,
        "total_assets": metrics.total_assets != metrics_raw.total_assets,
        "total_liabilities": metrics.total_liabilities != metrics_raw.total_liabilities,
    }

    return BaseResponse(
        success=True,
        message=f"DART API 원본 {len(statements)}개 항목, 주요 항목 {len(key_items)}개",
        data={
            "dart_status": data.get("status"),
            "total_items": len(statements),
            "key_items": key_items[:30],  # 상위 30개만
            "is_items": is_items,  # 손익계산서 전체 항목 (디버깅)
            "parsed_metrics": {
                "revenue": metrics.revenue,
                "operating_income": metrics.operating_income,
                "net_income": metrics.net_income,
                "total_assets": metrics.total_assets,
                "total_liabilities": metrics.total_liabilities,
                "total_equity": metrics.total_equity,
                "operating_cash_flow": metrics.operating_cash_flow,
            },
            "raw_metrics": {
                "net_income": metrics_raw.net_income,
                "total_equity": metrics_raw.total_equity,
            },
            "fallback_applied": fallback_applied,
            "calculated_ratios": {
                "roe_percent": round(roe, 2),
                "debt_ratio_percent": round(debt_ratio, 2),
            }
        }
    )


# ========================
# API 호출 / 분석 분리 엔드포인트
# ========================

@router.get("/v2/debug/csv-status")
async def debug_csv_status(
    year: str = Query("2023", description="사업연도"),
    fs_div: str = Query("CFS", description="재무제표 구분"),
    limit: int = Query(10, description="확인할 기업 수", ge=1, le=100),
):
    """디버그: CSV 파일 존재 여부 확인"""
    from shared.storage.csv_storage import csv_storage
    import os

    csv_status = []
    for corp_code, corp_name, stock_code, sector in COMPANIES[:limit]:
        params = {
            "corp_code": corp_code,
            "bsns_year": year,
            "reprt_code": "11011",
            "fs_div": fs_div
        }

        filepath = csv_storage._make_filepath("fnlttSinglAcntAll.json", params)
        exists = filepath.exists()
        size = os.path.getsize(filepath) if exists else 0

        csv_status.append({
            "corp_name": corp_name,
            "corp_code": corp_code,
            "csv_exists": exists,
            "csv_path": str(filepath),
            "size_bytes": size
        })

    csv_dir = csv_storage.csv_dir
    csv_files = list(csv_dir.glob("*.csv"))

    return BaseResponse(
        success=True,
        message=f"CSV 상태 확인 완료",
        data={
            "csv_directory": str(csv_dir),
            "total_csv_files": len(csv_files),
            "companies_checked": csv_status,
        }
    )


@router.post("/v2/fetch")
async def fetch_api_data(
    year: str = Query(..., description="사업연도"),
    fs_div: str = Query("CFS", description="재무제표 구분"),
    limit: int = Query(100, description="조회 개수", ge=1, le=4000),
    batch_size: int = Query(100, description="배치 크기 (기본 100, 속도 우선)", ge=1, le=500),
    max_concurrent: int = Query(100, description="최대 동시 요청 수 (기본 100, 속도 우선)", ge=1, le=500),
):
    """
    1단계: DART API 호출해서 CSV 저장만 (분석 안함)

    - CSV 파일이 이미 있으면 스킵
    - API 호출만 하고 점수 계산은 하지 않음
    - 나중에 /analyze 엔드포인트로 분석

    파라미터:
    - batch_size: 한 배치당 처리할 기업 수 (기본 100)
    - max_concurrent: API 동시 요청 수 (기본 100)
    """
    import time
    start_time = time.time()

    # max_concurrent는 프론트엔드 표시용, 실제로는 dart_client의 세마포어(100) 사용
    # 세마포어는 dart_client.py에서 고정값 100으로 설정됨 (속도 최우선)

    companies_to_fetch = COMPANIES[:limit] if limit < len(COMPANIES) else COMPANIES
    fetched_count = 0
    skipped_count = 0
    failed_corps = []

    # 병렬 API 호출
    async def fetch_company(corp_code, corp_name, stock_code, sector):
        nonlocal fetched_count, skipped_count

        # CSV 존재 확인
        params = {
            "corp_code": corp_code,
            "bsns_year": year,
            "reprt_code": "11011",
            "fs_div": fs_div
        }

        if csv_storage.file_exists("fnlttSinglAcntAll.json", params):
            skipped_count += 1
            return {"status": "skipped", "corp_name": corp_name}

        # API 호출 (dart_client가 자동으로 CSV 저장)
        try:
            data = await dart_client.get_financial_statements(
                corp_code=corp_code,
                bsns_year=year,
                reprt_code="11011",
                fs_div=fs_div
            )

            status = data.get("status", "unknown")
            message = data.get("message", "")

            if status == "000":
                fetched_count += 1
                print(f"[FETCH OK] {corp_name}")
                return {"status": "fetched", "corp_name": corp_name}
            else:
                error_msg = f"{corp_name} (status={status}, msg={message})"
                failed_corps.append(error_msg)
                print(f"[FETCH FAIL] {error_msg}")
                return {"status": "failed", "corp_name": corp_name, "error": message}

        except Exception as e:
            error_msg = f"{corp_name} (exception={str(e)[:50]})"
            failed_corps.append(error_msg)
            print(f"[FETCH ERROR] {error_msg}")
            return {"status": "error", "corp_name": corp_name, "error": str(e)[:50]}

    # 배치 처리 (동적 배치 크기)
    total_batches = (len(companies_to_fetch) + batch_size - 1) // batch_size
    for batch_idx, i in enumerate(range(0, len(companies_to_fetch), batch_size), 1):
        batch = companies_to_fetch[i:i+batch_size]
        tasks = [fetch_company(code, name, stock, sector) for code, name, stock, sector in batch]
        await asyncio.gather(*tasks)

        # 프로그레스 출력
        progress = (batch_idx / total_batches) * 100
        print(f"[PROGRESS] {batch_idx}/{total_batches} batches ({progress:.1f}%) - Fetched: {fetched_count}, Skipped: {skipped_count}, Failed: {len(failed_corps)}")

    elapsed = time.time() - start_time

    success = fetched_count > 0 or skipped_count > 0  # 하나라도 성공하면 success

    return BaseResponse(
        success=success,
        message=f"API 호출 완료: {fetched_count}개 fetch, {skipped_count}개 skip, {len(failed_corps)}개 fail ({elapsed:.1f}초)",
        data={
            "year": year,
            "fs_div": fs_div,
            "fetched_count": fetched_count,
            "skipped_count": skipped_count,
            "failed_count": len(failed_corps),
            "failed_corps": failed_corps,  # 전체 보여주기
            "elapsed_seconds": round(elapsed, 1),
            "total_companies": len(companies_to_fetch),
        }
    )


@router.post("/v2/analyze")
async def analyze_from_csv(
    year: str = Query(..., description="사업연도"),
    fs_div: str = Query("CFS", description="재무제표 구분"),
    limit: int = Query(100, description="조회 개수", ge=1, le=4000),
    batch_size: int = Query(100, description="배치 크기 (동시 처리 개수)", ge=1, le=500),
):
    """
    2단계: CSV에서 읽어서 점수 계산만 (API 호출 안함)

    - /fetch로 미리 받아둔 CSV 읽어서 분석
    - API 호출 없이 로컬 CSV만 사용
    - 결과는 buffett_analysis.csv에 저장

    파라미터:
    - batch_size: 한 배치당 처리할 기업 수 (기본 100)
    """
    import time
    start_time = time.time()

    companies_to_analyze = COMPANIES[:limit] if limit < len(COMPANIES) else COMPANIES
    results = []
    filtered_out = []
    no_csv_corps = []

    # 분석 함수 (CSV에서만 읽음)
    async def analyze_from_csv_file(corp_code, corp_name, stock_code, sector):
        # 1단계: 쓰레기 필터
        from features.companies.filter import is_trash_stock
        is_trash, trash_reason = is_trash_stock(corp_name, stock_code)

        if is_trash:
            save_buffett_analysis(
                corp_code=corp_code,
                corp_name=corp_name,
                stock_code=stock_code,
                sector=sector,
                bsns_year=year,
                fs_div=fs_div,
                total_score=0,
                signal="투자금지",
                filter_passed=False,
                filter_reasons=[f"쓰레기주식: {trash_reason}"],
                indicators={},
                data_source="1단계 필터 탈락",
            )
            return {
                "corp_name": corp_name,
                "filter_passed": False,
                "no_csv": False,
            }

        # CSV 존재 확인
        params = {
            "corp_code": corp_code,
            "bsns_year": year,
            "reprt_code": "11011",
            "fs_div": fs_div
        }

        if not csv_storage.file_exists("fnlttSinglAcntAll.json", params):
            no_csv_corps.append(corp_name)
            return {"corp_name": corp_name, "no_csv": True}

        # 분석 (financial_analyzer가 CSV에서 읽음)
        try:
            result = await financial_analyzer.analyze(corp_code, corp_name, year, fs_div)

            if result:
                # 지표 딕셔너리 생성
                indicators_dict = {
                    indicator.name: {
                        "value": indicator.value,
                        "score": indicator.score,
                        "max_score": indicator.max_score,
                        "grade": indicator.grade,
                        "description": indicator.description,
                        "category": indicator.category,
                    }
                    for indicator in result.indicators
                }

                # DB 저장
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
                    data_source=result.data_source,
                )

                return {
                    "corp_name": corp_name,
                    "filter_passed": result.filter_result.passed,
                    "total_score": result.total_score,
                    "no_csv": False,
                }
            else:
                return {"corp_name": corp_name, "no_csv": True}

        except Exception as e:
            print(f"[ANALYZE ERROR] {corp_name}: {e}")
            return {"corp_name": corp_name, "no_csv": True}

    # 배치 처리 (동적 배치 크기)
    for i in range(0, len(companies_to_analyze), batch_size):
        batch = companies_to_analyze[i:i+batch_size]
        tasks = [analyze_from_csv_file(code, name, stock, sector) for code, name, stock, sector in batch]
        batch_results = await asyncio.gather(*tasks)

        for item in batch_results:
            if item.get("no_csv"):
                no_csv_corps.append(item["corp_name"])
            elif item.get("filter_passed"):
                results.append(item)
            else:
                filtered_out.append(item)

    elapsed = time.time() - start_time

    # CSV flush
    csv_storage._flush_results()

    return BaseResponse(
        success=True,
        message=f"분석 완료: {len(results)}개 통과, {len(filtered_out)}개 필터 탈락, {len(no_csv_corps)}개 CSV 없음 ({elapsed:.1f}초)",
        data={
            "year": year,
            "fs_div": fs_div,
            "passed_count": len(results),
            "filtered_count": len(filtered_out),
            "no_csv_count": len(no_csv_corps),
            "no_csv_corps": no_csv_corps[:30],
            "elapsed_seconds": round(elapsed, 1),
        }
    )
