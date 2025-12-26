"""트렌드 분석 및 우량주 스캔 서비스"""

from datetime import datetime
from shared.api.dart_client import dart_client
from shared.utils.parsers import parse_amount
from features.indicators.service import indicator_service
from shared.schemas.indicators import SignalType


# 주요 기업 목록 (고유번호, 기업명, 종목코드)
MAJOR_COMPANIES = [
    ("00126380", "삼성전자", "005930"),
    ("00164742", "현대자동차", "005380"),
    ("00164779", "기아", "000270"),
    ("00401731", "SK하이닉스", "000660"),
    ("00145765", "POSCO홀딩스", "005490"),
    ("00155355", "네이버", "035420"),
    ("00181710", "카카오", "035720"),
    ("00356361", "LG에너지솔루션", "373220"),
    ("00104217", "삼성바이오로직스", "207940"),
    ("00126186", "LG화학", "051910"),
    ("00107367", "셀트리온", "068270"),
    ("00164830", "HD현대중공업", "329180"),
    ("00138249", "삼성SDI", "006400"),
    ("00102640", "현대모비스", "012330"),
    ("00140772", "KB금융", "105560"),
]


class TrendService:
    """트렌드 분석 서비스"""

    def __init__(self):
        self.client = dart_client

    async def get_multi_year_data(
        self, corp_code: str, years: list[str], fs_div: str = "OFS"
    ) -> dict:
        """다년간 재무 데이터 조회"""
        results = {}

        for year in years:
            try:
                data = await self.client.get_financial_statements(
                    corp_code=corp_code,
                    bsns_year=year,
                    reprt_code="11011",
                    fs_div=fs_div,
                )

                if data.get("status") == "000":
                    statements = data.get("list", [])

                    year_data = {
                        "operating_income": 0,
                        "net_income": 0,
                        "operating_cash_flow": 0,
                        "interest_expense": 0,
                        "total_equity": 0,
                        "total_assets": 0,
                    }

                    for item in statements:
                        account_id = item.get("account_id", "")
                        account_nm = item.get("account_nm", "")
                        sj_div = item.get("sj_div", "")

                        if account_id == "dart_OperatingIncomeLoss" and sj_div == "IS":
                            year_data["operating_income"] = parse_amount(item.get("thstrm_amount"))

                        if account_id == "ifrs_ProfitLoss" and sj_div == "CIS":
                            year_data["net_income"] = parse_amount(item.get("thstrm_amount"))

                        if account_id == "ifrs_CashFlowsFromUsedInOperatingActivities" and sj_div == "CF":
                            year_data["operating_cash_flow"] = parse_amount(item.get("thstrm_amount"))

                        if sj_div == "IS" and "금융비용" in account_nm:
                            year_data["interest_expense"] = parse_amount(item.get("thstrm_amount"))

                        if account_id == "ifrs_Equity" and sj_div == "BS":
                            year_data["total_equity"] = parse_amount(item.get("thstrm_amount"))

                        if account_id == "ifrs_Assets" and sj_div == "BS":
                            year_data["total_assets"] = parse_amount(item.get("thstrm_amount"))

                    results[year] = year_data
            except Exception as e:
                print(f"Error fetching {year} data: {e}")

        return results

    async def analyze_trend(
        self, corp_code: str, corp_name: str, current_year: str, fs_div: str = "OFS"
    ) -> dict:
        """트렌드 분석 (3개년)"""
        years = [str(int(current_year) - i) for i in range(3)]
        multi_year = await self.get_multi_year_data(corp_code, years, fs_div)

        if len(multi_year) < 2:
            return {"error": "데이터 부족"}

        trends = []
        prev_data = None

        for year in sorted(multi_year.keys()):
            data = multi_year[year]
            trend_item = {"year": year, **data}

            if prev_data:
                # 성장률 계산
                if prev_data["operating_income"] != 0:
                    trend_item["op_growth"] = (
                        (data["operating_income"] - prev_data["operating_income"])
                        / abs(prev_data["operating_income"])
                        * 100
                    )
                else:
                    trend_item["op_growth"] = 0

                if prev_data["net_income"] != 0:
                    trend_item["ni_growth"] = (
                        (data["net_income"] - prev_data["net_income"])
                        / abs(prev_data["net_income"])
                        * 100
                    )
                else:
                    trend_item["ni_growth"] = 0

            # 이자보상배율
            if data["interest_expense"] != 0:
                trend_item["interest_coverage"] = data["operating_income"] / data["interest_expense"]
            else:
                trend_item["interest_coverage"] = 999

            # 현금흐름 > 순이익
            trend_item["cash_quality"] = data["operating_cash_flow"] > data["net_income"]

            trends.append(trend_item)
            prev_data = data

        # 트렌드 판정
        if len(trends) >= 2:
            latest = trends[-1]
            previous = trends[-2]

            improving = []
            declining = []

            # 영업이익 추세
            if latest.get("op_growth", 0) > previous.get("op_growth", 0):
                improving.append("영업이익 성장세 개선")
            elif latest.get("op_growth", 0) < previous.get("op_growth", 0):
                declining.append("영업이익 성장세 둔화")

            # 이자보상배율 추세
            if latest.get("interest_coverage", 0) > previous.get("interest_coverage", 0):
                improving.append("재무안정성 개선")
            elif latest.get("interest_coverage", 0) < previous.get("interest_coverage", 0):
                declining.append("재무안정성 악화")

            # 현금흐름 품질
            if latest.get("cash_quality") and not previous.get("cash_quality"):
                improving.append("현금흐름 품질 개선")
            elif not latest.get("cash_quality") and previous.get("cash_quality"):
                declining.append("현금흐름 품질 악화")

            trend_signal = "improving" if len(improving) > len(declining) else "declining" if len(declining) > len(improving) else "stable"
        else:
            improving = []
            declining = []
            trend_signal = "unknown"

        return {
            "corp_code": corp_code,
            "corp_name": corp_name,
            "trends": trends,
            "improving": improving,
            "declining": declining,
            "trend_signal": trend_signal,
        }


class StockScreenerService:
    """우량주 스캔 서비스"""

    async def scan_stocks(self, year: str, fs_div: str = "OFS", limit: int = 10) -> list:
        """우량주 스캔"""
        results = []

        for corp_code, corp_name, stock_code in MAJOR_COMPANIES:
            try:
                analysis = await indicator_service.get_comprehensive_analysis(
                    corp_code=corp_code,
                    corp_name=corp_name,
                    bsns_year=year,
                    fs_div=fs_div,
                )

                results.append({
                    "corp_code": corp_code,
                    "corp_name": corp_name,
                    "stock_code": stock_code,
                    "score": analysis.overall_score,
                    "signal": analysis.overall_signal.value,
                    "recommendation": analysis.recommendation,
                    "cash_generation": analysis.cash_generation.signal.value if analysis.cash_generation else None,
                    "interest_coverage": analysis.interest_coverage.ratio if analysis.interest_coverage else None,
                    "operating_growth": analysis.operating_profit_growth.growth_rate if analysis.operating_profit_growth else None,
                })
            except Exception as e:
                print(f"Error scanning {corp_name}: {e}")

        # 점수순 정렬
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    async def get_top_picks(self, year: str, fs_div: str = "OFS") -> list:
        """상위 추천 종목"""
        all_stocks = await self.scan_stocks(year, fs_div, limit=len(MAJOR_COMPANIES))

        # 점수 70점 이상만 필터링
        return [s for s in all_stocks if s["score"] >= 70]


# 싱글톤
trend_service = TrendService()
stock_screener = StockScreenerService()
