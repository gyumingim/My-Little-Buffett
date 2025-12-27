"""백테스팅 API 라우터

과거 지표로 선정된 종목들이 실제로 수익률이 좋았는지 검증합니다.
"""

from fastapi import APIRouter, Query
from typing import Optional
from datetime import datetime, timedelta
from shared.api.stock_price_client import stock_price_client
from shared.cache import get_buffett_analysis
from shared.schemas import BaseResponse

router = APIRouter(tags=["backtest"])


@router.get("/validate")
async def validate_strategy(
    year: str = Query(..., description="분석 연도 (예: 2021)"),
    fs_div: str = Query("CFS", description="재무제표 구분 (CFS/OFS)"),
    top_n: int = Query(20, description="상위 몇 개 종목을 검증할지"),
    holding_years: int = Query(3, description="몇 년 보유했는지 (기본 3년)")
):
    """
    과거 특정 연도의 지표로 선정된 종목들의 수익률 검증

    흐름:
    1. DB에서 해당 연도의 분석 결과 조회 (상위 top_n개)
    2. 공시일(다음해 4월) 기준 주가 조회
    3. holding_years 후 주가와 비교하여 수익률 계산
    4. 평균 수익률, 승률 등 통계 반환
    """
    # 1. DB에서 해당 연도 분석 결과 조회
    all_results = get_buffett_analysis(year, fs_div)

    if not all_results:
        return BaseResponse(
            success=False,
            message=f"{year}년 {fs_div} 데이터가 없습니다. 먼저 스크리너를 실행해주세요.",
            data={}
        )

    # 필터 통과한 종목만 선택 (signal != "데이터없음")
    filtered = [r for r in all_results if r.get("signal") != "데이터없음" and r.get("filter_passed")]

    # 점수순 정렬
    filtered.sort(key=lambda x: x.get("total_score", 0), reverse=True)

    # 상위 top_n개 선택
    top_stocks = filtered[:top_n]

    if not top_stocks:
        return BaseResponse(
            success=False,
            message=f"{year}년에 필터를 통과한 종목이 없습니다.",
            data={}
        )

    # 2. 매수 시점: 다음해 4월 1일 (사업보고서 공시 직후)
    buy_year = int(year) + 1
    buy_date = f"{buy_year}-04-01"

    # 매도 시점: holding_years 후
    sell_year = buy_year + holding_years
    sell_date = datetime.now().strftime("%Y-%m-%d") if sell_year > datetime.now().year else f"{sell_year}-04-01"

    # 3. 각 종목별 수익률 계산
    results = []
    total_return = 0
    win_count = 0
    valid_count = 0

    for stock in top_stocks:
        stock_code = stock.get("stock_code")
        corp_name = stock.get("corp_name")
        total_score = stock.get("total_score", 0)
        signal = stock.get("signal", "")

        if not stock_code or stock_code == "N/A":
            continue

        # 주가 수익률 조회
        return_data = stock_price_client.get_return_rate(stock_code, buy_date, sell_date)

        if return_data:
            return_rate = return_data["return_rate"]
            total_return += return_rate
            valid_count += 1

            if return_rate > 0:
                win_count += 1

            results.append({
                "corp_name": corp_name,
                "stock_code": stock_code,
                "total_score": round(total_score, 2),
                "signal": signal,
                "buy_date": return_data["start_date"],
                "buy_price": return_data["start_price"],
                "sell_date": return_data["end_date"],
                "sell_price": return_data["end_price"],
                "return_rate": return_rate
            })
        else:
            results.append({
                "corp_name": corp_name,
                "stock_code": stock_code,
                "total_score": round(total_score, 2),
                "signal": signal,
                "error": "주가 데이터 없음"
            })

    # 4. 통계 계산
    avg_return = total_return / valid_count if valid_count > 0 else 0
    win_rate = (win_count / valid_count * 100) if valid_count > 0 else 0

    # KOSPI 수익률 (비교 기준) - 코스피 지수는 종목코드 "KS11"
    kospi_return = stock_price_client.get_return_rate("KS11", buy_date, sell_date)
    kospi_rate = kospi_return["return_rate"] if kospi_return else 0

    return BaseResponse(
        success=True,
        message=f"{year}년 상위 {top_n}개 종목 백테스팅 완료",
        data={
            "config": {
                "year": year,
                "fs_div": fs_div,
                "top_n": top_n,
                "holding_years": holding_years,
                "buy_date": buy_date,
                "sell_date": sell_date
            },
            "statistics": {
                "total_stocks": len(results),
                "valid_stocks": valid_count,
                "avg_return": round(avg_return, 2),
                "win_count": win_count,
                "win_rate": round(win_rate, 2),
                "kospi_return": round(kospi_rate, 2),
                "alpha": round(avg_return - kospi_rate, 2)  # 초과 수익률
            },
            "stocks": results
        }
    )


@router.get("/years")
async def get_available_years():
    """
    DB에 저장된 분석 연도 목록 조회
    """
    # 2018년부터 현재까지 연도 목록 반환
    current_year = datetime.now().year
    years = [str(y) for y in range(2018, current_year)]

    return BaseResponse(
        success=True,
        message=f"{len(years)}개 연도 조회 가능",
        data={"years": years}
    )
