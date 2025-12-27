"""주가 데이터 클라이언트 (FinanceDataReader 사용)

한국 거래소(KRX) 주가 데이터를 가져와 캐싱합니다.
"""

import FinanceDataReader as fdr
from datetime import datetime, timedelta
from typing import Optional
from shared.cache import get_stored, store_data


class StockPriceClient:
    """주가 데이터 클라이언트 (DB 캐싱)"""

    def get_price_at_date(self, stock_code: str, target_date: str) -> Optional[float]:
        """
        특정 날짜의 주가(종가) 조회

        Args:
            stock_code: 종목코드 (6자리, 예: "005930")
            target_date: 날짜 (YYYY-MM-DD)

        Returns:
            해당 날짜의 종가, 데이터 없으면 None
        """
        # DB 캐시 확인
        cache_key = f"stock_price_{stock_code}_{target_date}"
        stored = get_stored("stock_price", {"stock_code": stock_code, "date": target_date})
        if stored and "price" in stored:
            return stored["price"]

        try:
            # 해당 날짜 전후 5일 범위에서 데이터 조회 (주말/공휴일 대응)
            target = datetime.strptime(target_date, "%Y-%m-%d")
            start_date = (target - timedelta(days=5)).strftime("%Y-%m-%d")
            end_date = (target + timedelta(days=5)).strftime("%Y-%m-%d")

            df = fdr.DataReader(stock_code, start_date, end_date)

            if df.empty:
                # 데이터 없음도 캐싱 (반복 조회 방지)
                store_data("stock_price", {"stock_code": stock_code, "date": target_date}, {"price": None})
                return None

            # 가장 가까운 날짜의 종가 선택
            df.index = df.index.map(lambda x: x.strftime("%Y-%m-%d"))
            if target_date in df.index:
                price = float(df.loc[target_date]["Close"])
            else:
                # 가장 가까운 날짜 찾기
                price = float(df.iloc[0]["Close"])

            # 캐싱
            store_data("stock_price", {"stock_code": stock_code, "date": target_date}, {"price": price})
            return price

        except Exception as e:
            print(f"[STOCK PRICE ERROR] {stock_code} at {target_date}: {e}")
            return None

    def get_return_rate(
        self,
        stock_code: str,
        start_date: str,
        end_date: str = None
    ) -> Optional[dict]:
        """
        기간별 수익률 계산

        Args:
            stock_code: 종목코드
            start_date: 시작일 (매수 시점, YYYY-MM-DD)
            end_date: 종료일 (매도 시점, YYYY-MM-DD, 기본값: 오늘)

        Returns:
            {
                "start_price": 시작가,
                "end_price": 종료가,
                "return_rate": 수익률(%),
                "start_date": 실제 시작일,
                "end_date": 실제 종료일
            }
        """
        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")

        # DB 캐시 확인
        cache_key = f"return_rate_{stock_code}_{start_date}_{end_date}"
        stored = get_stored("return_rate", {
            "stock_code": stock_code,
            "start_date": start_date,
            "end_date": end_date
        })
        if stored and "return_rate" in stored:
            return stored

        try:
            # 주가 데이터 가져오기
            df = fdr.DataReader(stock_code, start_date, end_date)

            if df.empty or len(df) < 2:
                return None

            start_price = float(df.iloc[0]["Close"])
            end_price = float(df.iloc[-1]["Close"])
            return_rate = ((end_price - start_price) / start_price) * 100

            actual_start = df.index[0].strftime("%Y-%m-%d")
            actual_end = df.index[-1].strftime("%Y-%m-%d")

            result = {
                "start_price": round(start_price, 2),
                "end_price": round(end_price, 2),
                "return_rate": round(return_rate, 2),
                "start_date": actual_start,
                "end_date": actual_end
            }

            # 캐싱
            store_data("return_rate", {
                "stock_code": stock_code,
                "start_date": start_date,
                "end_date": end_date
            }, result)

            return result

        except Exception as e:
            print(f"[RETURN RATE ERROR] {stock_code} ({start_date} ~ {end_date}): {e}")
            return None


# 싱글톤 인스턴스
stock_price_client = StockPriceClient()
