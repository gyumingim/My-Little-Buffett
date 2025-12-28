"""
CSV 전용 버전 - API 호출 없음

웹사이트는 CSV 파일만 읽어서 분석합니다.
데이터 수집은 별도 스크립트 (fetch_dart_data.py)를 사용하세요.

/screener?year=2024&limit=100
  → CSV 파일에서 데이터 읽기
  → 분석
  → 결과 반환
"""

from fastapi import APIRouter, Query
from features.companies.data import COMPANIES
from shared.schemas.common import BaseResponse
from shared.storage.csv_storage import csv_storage
from shared.cache import save_buffett_analysis, get_buffett_analysis, get_buffett_analysis_count
from features.indicators.analyzer import BuffettAnalyzer
import asyncio

router = APIRouter()
financial_analyzer = BuffettAnalyzer()


@router.get("/screener")
async def csv_only_screener(
    year: str = Query(..., description="사업연도 (예: 2024)"),
    limit: int = Query(100, description="분석할 기업 수", ge=1, le=4000),
    batch_size: int = Query(100, description="배치 크기", ge=1, le=500),
    force_reanalyze: bool = Query(False, description="캐시 무시하고 재분석"),
):
    """
    🎯 CSV 전용 스크리너 - API 호출 없음

    CSV 파일만 읽어서 분석합니다.

    1. 캐시된 분석 결과가 있으면 바로 반환
    2. 없으면 CSV 파일에서 데이터 읽어서 분석
    3. CSV 파일이 없으면 → "데이터 없음" 처리

    ⚠️ 새로운 데이터를 수집하려면:
       → fetch_dart_data.py 스크립트를 별도로 실행하세요
    """
    # 1. 캐시된 분석 결과 확인 (force_reanalyze=False일 때만)
    if not force_reanalyze:
        cached_count = get_buffett_analysis_count(year, None)
        if cached_count > 0:
            cached = get_buffett_analysis(year, None)
            results = [r for r in cached if r["filter_passed"]][:limit]
            filtered_out = [r for r in cached if not r["filter_passed"]][:20]

            for i, r in enumerate(results, 1):
                r["rank"] = i

            return BaseResponse(
                success=True,
                message=f"📊 {len(results)}개 우량주 / {len(filtered_out)}개 필터 탈락 (캐시됨)",
                data={
                    "year": year,
                    "stocks": results,
                    "filtered_out": filtered_out,
                    "total_analyzed": cached_count,
                    "from_cache": True,
                }
            )

    # 2. 캐시 없으면 CSV에서 분석
    companies = COMPANIES[:limit]
    total_batches = (len(companies) + batch_size - 1) // batch_size

    print(f"\n[CSV 분석 시작] {year}년, {len(companies)}개 기업")

    for batch_idx, i in enumerate(range(0, len(companies), batch_size), 1):
        batch = companies[i:i+batch_size]

        # 배치 처리
        async def process_company(corp_code, corp_name, stock_code, sector):
            """CSV에서 데이터 읽어서 분석 (API 호출 없음)"""

            # 쓰레기 필터 체크
            from features.companies.filter import is_trash_stock
            is_trash, trash_reason = is_trash_stock(corp_name, stock_code)

            if is_trash:
                save_buffett_analysis(
                    corp_code=corp_code, corp_name=corp_name, stock_code=stock_code,
                    sector=sector, bsns_year=year, fs_div="N/A",
                    total_score=0, signal="투자금지", filter_passed=False,
                    filter_reasons=[f"쓰레기: {trash_reason}"], indicators={},
                    data_source="필터 탈락"
                )
                return {"name": corp_name, "status": "filtered"}

            try:
                # CSV에서 분석 (API 호출 없음)
                result = await financial_analyzer.analyze(corp_code, corp_name, year)

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

                    save_buffett_analysis(
                        corp_code=corp_code, corp_name=corp_name, stock_code=stock_code,
                        sector=sector, bsns_year=year, fs_div=result.fs_div,
                        total_score=result.total_score, signal=result.signal,
                        filter_passed=result.filter_result.passed,
                        filter_reasons=result.filter_result.failed_reasons,
                        indicators=indicators_dict, data_source=result.data_source
                    )

                    if result.filter_result.passed:
                        return {"name": corp_name, "status": "passed", "score": result.total_score}
                    else:
                        return {"name": corp_name, "status": "filtered"}
                else:
                    # CSV 파일 없음 → 데이터 수집 스크립트 실행 필요
                    save_buffett_analysis(
                        corp_code=corp_code, corp_name=corp_name, stock_code=stock_code,
                        sector=sector, bsns_year=year, fs_div="N/A",
                        total_score=0, signal="데이터없음", filter_passed=False,
                        filter_reasons=[f"CSV 파일 없음 - fetch_dart_data.py 실행 필요"],
                        indicators={}, data_source="CSV 없음"
                    )
                    return {"name": corp_name, "status": "no_csv"}

            except Exception as e:
                print(f"[ERROR] {corp_name}: {e}")
                return {"name": corp_name, "status": "error"}

        # 배치 실행
        tasks = [process_company(code, name, stock, sector) for code, name, stock, sector in batch]
        batch_results = await asyncio.gather(*tasks)

        # 진행상황 출력
        passed = sum(1 for r in batch_results if r.get("status") == "passed")
        filtered = sum(1 for r in batch_results if r.get("status") == "filtered")
        no_csv = sum(1 for r in batch_results if r.get("status") == "no_csv")

        print(f"[{batch_idx}/{total_batches}] 통과: {passed}, 탈락: {filtered}, CSV없음: {no_csv}")

    # 3. 결과 반환
    csv_storage._flush_results()

    final_results = get_buffett_analysis(year, None)
    stocks = [r for r in final_results if r["filter_passed"]][:limit]
    filtered = [r for r in final_results if not r["filter_passed"]][:20]

    # CSV 없는 기업 카운트
    no_csv_count = sum(1 for r in final_results if "CSV 파일 없음" in str(r.get("filter_reasons", [])))

    for i, r in enumerate(stocks, 1):
        r["rank"] = i

    message = f"✅ 분석 완료: {len(stocks)}개 우량주 / {len(filtered)}개 필터 탈락"
    if no_csv_count > 0:
        message += f" (⚠️ {no_csv_count}개 CSV 없음)"

    return BaseResponse(
        success=True,
        message=message,
        data={
            "year": year,
            "stocks": stocks,
            "filtered_out": filtered,
            "total_analyzed": len(final_results),
            "from_cache": False,
            "no_csv_count": no_csv_count,
        }
    )


@router.get("/stats")
async def get_csv_stats():
    """
    CSV 파일 통계 정보

    몇 개의 CSV 파일이 있는지, 어떤 연도가 있는지 등을 확인합니다.
    """
    import os
    from pathlib import Path

    csv_dir = Path(__file__).parent.parent.parent / "data" / "csv"

    if not csv_dir.exists():
        return BaseResponse(
            success=True,
            message="CSV 디렉토리가 없습니다",
            data={"csv_count": 0, "years": []}
        )

    # CSV 파일 카운트
    csv_files = list(csv_dir.glob("*.csv"))

    # 연도별 그룹화
    year_counts = {}
    for csv_file in csv_files:
        # 파일명 형식: 2024_fnlttSinglAcntAll_00123456_CFS_11011.csv
        parts = csv_file.stem.split("_")
        if len(parts) >= 1:
            year = parts[0]
            year_counts[year] = year_counts.get(year, 0) + 1

    return BaseResponse(
        success=True,
        message=f"CSV 파일 {len(csv_files)}개",
        data={
            "csv_count": len(csv_files),
            "years": sorted(year_counts.keys(), reverse=True),
            "year_counts": year_counts,
        }
    )
