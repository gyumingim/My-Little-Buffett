"""5대 투자 지표 계산 서비스"""

from datetime import datetime, timedelta
from shared.api.dart_client import dart_client
from shared.schemas.indicators import (
    SignalType,
    CashGenerationIndicator,
    InterestCoverageIndicator,
    OperatingProfitGrowthIndicator,
    DilutionRiskIndicator,
    InsiderTradingIndicator,
    ComprehensiveAnalysis,
)
from shared.utils.parsers import parse_amount, parse_int


class IndicatorService:
    """5대 지표 계산 서비스"""

    def __init__(self):
        self.client = dart_client

    async def calculate_cash_generation(
        self, corp_code: str, bsns_year: str, fs_div: str = "OFS"
    ) -> CashGenerationIndicator | None:
        """
        1. 현금 창출 능력 지표 계산
        - 영업활동현금흐름 > 당기순이익 (필수 조건)
        """
        try:
            data = await self.client.get_financial_statements(
                corp_code=corp_code,
                bsns_year=bsns_year,
                reprt_code="11011",
                fs_div=fs_div,
            )

            if data.get("status") != "000":
                return None

            statements = data.get("list", [])

            # 영업활동 현금흐름 (CF)
            operating_cash_flow = 0.0
            net_income = 0.0

            for item in statements:
                account_id = item.get("account_id", "")
                sj_div = item.get("sj_div", "")

                # 영업활동 현금흐름
                if account_id == "ifrs_CashFlowsFromUsedInOperatingActivities" and sj_div == "CF":
                    operating_cash_flow = parse_amount(item.get("thstrm_amount"))

                # 당기순이익 (CIS에서 가져오기)
                if account_id == "ifrs_ProfitLoss" and sj_div == "CIS":
                    net_income = parse_amount(item.get("thstrm_amount"))

            is_greater = operating_cash_flow > net_income

            if is_greater:
                signal = SignalType.BUY
                signal_desc = "영업활동현금흐름이 당기순이익보다 큽니다. 현금 창출 능력이 우수합니다."
            else:
                signal = SignalType.CAUTION
                signal_desc = "영업활동현금흐름이 당기순이익보다 작습니다. 매출채권 회수나 재고 관리에 주의가 필요합니다."

            return CashGenerationIndicator(
                name="현금 창출 능력",
                description="영업활동현금흐름 vs 당기순이익",
                signal=signal,
                signal_description=signal_desc,
                operating_cash_flow=operating_cash_flow,
                net_income=net_income,
                is_cash_flow_greater=is_greater,
                consecutive_warning_years=0 if is_greater else 1,
            )

        except Exception as e:
            print(f"Error calculating cash generation: {e}")
            return None

    async def calculate_interest_coverage(
        self, corp_code: str, bsns_year: str, fs_div: str = "OFS"
    ) -> InterestCoverageIndicator | None:
        """
        2. 이자보상배율 계산
        - 영업이익 ÷ 이자비용
        - > 3.0: 매우 안전
        - > 1.5: 최소 기준
        - < 1.0: 좀비 기업
        """
        try:
            data = await self.client.get_financial_statements(
                corp_code=corp_code,
                bsns_year=bsns_year,
                reprt_code="11011",
                fs_div=fs_div,
            )

            if data.get("status") != "000":
                return None

            statements = data.get("list", [])

            operating_income = 0.0
            interest_expense = 0.0

            for item in statements:
                account_id = item.get("account_id", "")
                account_nm = item.get("account_nm", "")
                sj_div = item.get("sj_div", "")

                # 영업이익 (IS)
                if account_id == "dart_OperatingIncomeLoss" and sj_div == "IS":
                    operating_income = parse_amount(item.get("thstrm_amount"))

                # 금융비용/이자비용 (IS) - 표준계정코드 미사용인 경우도 처리
                if sj_div == "IS" and "금융비용" in account_nm:
                    interest_expense = parse_amount(item.get("thstrm_amount"))

            # 이자비용이 0이면 무한대 (안전)
            if interest_expense == 0:
                ratio = float("inf") if operating_income > 0 else 0
            else:
                ratio = operating_income / interest_expense

            if ratio >= 3.0:
                signal = SignalType.STRONG_BUY
                signal_desc = f"이자보상배율 {ratio:.2f}배로 매우 안전합니다."
            elif ratio >= 1.5:
                signal = SignalType.BUY
                signal_desc = f"이자보상배율 {ratio:.2f}배로 최소 기준을 충족합니다."
            elif ratio >= 1.0:
                signal = SignalType.CAUTION
                signal_desc = f"이자보상배율 {ratio:.2f}배로 주의가 필요합니다."
            else:
                signal = SignalType.STRONG_SELL
                signal_desc = f"이자보상배율 {ratio:.2f}배로 이자도 못 갚는 좀비 기업입니다. 투자 금지!"

            return InterestCoverageIndicator(
                name="이자보상배율",
                description="영업이익 ÷ 이자비용",
                signal=signal,
                signal_description=signal_desc,
                operating_income=operating_income,
                interest_expense=interest_expense,
                ratio=ratio if ratio != float("inf") else 999.99,
            )

        except Exception as e:
            print(f"Error calculating interest coverage: {e}")
            return None

    async def calculate_operating_profit_growth(
        self, corp_code: str, bsns_year: str, fs_div: str = "OFS"
    ) -> OperatingProfitGrowthIndicator | None:
        """
        3. 영업이익 성장률 계산
        - (당기 - 전기) ÷ 전기 × 100
        - ≥ 15%: 고성장주
        - 0-10%: 일반 성장
        - < 0%: 역성장
        """
        try:
            data = await self.client.get_financial_statements(
                corp_code=corp_code,
                bsns_year=bsns_year,
                reprt_code="11011",
                fs_div=fs_div,
            )

            if data.get("status") != "000":
                return None

            statements = data.get("list", [])

            current_income = 0.0
            previous_income = 0.0

            for item in statements:
                account_id = item.get("account_id", "")
                sj_div = item.get("sj_div", "")

                if account_id == "dart_OperatingIncomeLoss" and sj_div == "IS":
                    current_income = parse_amount(item.get("thstrm_amount"))
                    previous_income = parse_amount(item.get("frmtrm_amount"))
                    break

            # 전기 영업이익이 0이면 성장률 계산 불가
            if previous_income == 0:
                growth_rate = 0.0 if current_income == 0 else 100.0
            else:
                growth_rate = ((current_income - previous_income) / abs(previous_income)) * 100

            if growth_rate >= 15:
                signal = SignalType.STRONG_BUY
                signal_desc = f"영업이익 성장률 {growth_rate:.1f}%로 고성장주입니다."
            elif growth_rate >= 10:
                signal = SignalType.BUY
                signal_desc = f"영업이익 성장률 {growth_rate:.1f}%로 양호한 성장세입니다."
            elif growth_rate >= 0:
                signal = SignalType.HOLD
                signal_desc = f"영업이익 성장률 {growth_rate:.1f}%로 일반적인 성장입니다."
            else:
                signal = SignalType.SELL
                signal_desc = f"영업이익 성장률 {growth_rate:.1f}%로 역성장 중입니다."

            return OperatingProfitGrowthIndicator(
                name="영업이익 성장률",
                description="(당기 영업이익 - 전기 영업이익) ÷ 전기 영업이익 × 100",
                signal=signal,
                signal_description=signal_desc,
                current_operating_income=current_income,
                previous_operating_income=previous_income,
                growth_rate=growth_rate,
            )

        except Exception as e:
            print(f"Error calculating operating profit growth: {e}")
            return None

    async def calculate_dilution_risk(
        self, corp_code: str, bsns_year: str
    ) -> DilutionRiskIndicator | None:
        """
        4. 희석 가능 물량 비율 계산
        - 전환사채 주식수 ÷ 총 발행 주식수 × 100
        - 0%: 가장 좋음
        - < 5%: 감내 가능
        - ≥ 10%: 투자 주의
        """
        try:
            # 전환사채 정보 조회
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")

            cb_data = await self.client.get_convertible_bond(
                corp_code=corp_code, bgn_de=start_date, end_de=end_date
            )

            convertible_shares = 0
            if cb_data.get("status") == "000":
                for item in cb_data.get("list", []):
                    shares = parse_int(item.get("ovis_ster", "0"))
                    convertible_shares += shares

            # 재무제표에서 자본금으로 총 주식수 추정
            fs_data = await self.client.get_financial_statements(
                corp_code=corp_code,
                bsns_year=bsns_year,
                reprt_code="11011",
                fs_div="OFS",
            )

            total_shares = 0
            if fs_data.get("status") == "000":
                for item in fs_data.get("list", []):
                    if item.get("account_id") == "ifrs_IssuedCapital":
                        # 자본금 / 액면가(보통 5000원)로 추정
                        capital = parse_amount(item.get("thstrm_amount"))
                        total_shares = int(capital / 5000) if capital > 0 else 0
                        break

            if total_shares == 0:
                total_shares = 1  # 0으로 나누기 방지

            dilution_ratio = (convertible_shares / total_shares) * 100

            if dilution_ratio == 0:
                signal = SignalType.STRONG_BUY
                signal_desc = "전환사채가 없어 희석 위험이 없습니다."
            elif dilution_ratio < 5:
                signal = SignalType.BUY
                signal_desc = f"희석 비율 {dilution_ratio:.1f}%로 감내 가능한 수준입니다."
            elif dilution_ratio < 10:
                signal = SignalType.CAUTION
                signal_desc = f"희석 비율 {dilution_ratio:.1f}%로 주의가 필요합니다."
            else:
                signal = SignalType.SELL
                signal_desc = f"희석 비율 {dilution_ratio:.1f}%로 주가 상승시 매물 출회 우려가 있습니다."

            return DilutionRiskIndicator(
                name="희석 가능 물량 비율",
                description="전환사채 주식수 ÷ 총 발행 주식수 × 100",
                signal=signal,
                signal_description=signal_desc,
                convertible_shares=convertible_shares,
                total_shares=total_shares,
                dilution_ratio=dilution_ratio,
            )

        except Exception as e:
            print(f"Error calculating dilution risk: {e}")
            return None

    async def calculate_insider_trading(
        self, corp_code: str
    ) -> InsiderTradingIndicator | None:
        """
        5. 임원/주요주주 순매수 강도 계산
        - 최근 3-6개월 내 장내매수 카운트
        - 2인 이상 순매수 또는 CEO 매수: 호재
        - 지속적 매도: 악재
        """
        try:
            data = await self.client.get_executive_stock(corp_code=corp_code)

            if data.get("status") != "000":
                return None

            # 최근 6개월 필터링
            six_months_ago = datetime.now() - timedelta(days=180)

            net_buy_executives = []
            net_sell_count = 0
            ceo_bought = False

            for item in data.get("list", []):
                # 날짜 필터링
                report_date = item.get("rcept_dt", "")
                try:
                    report_datetime = datetime.strptime(report_date, "%Y-%m-%d")
                    if report_datetime < six_months_ago:
                        continue
                except:
                    continue

                # 증감 수량 파싱
                change_count = parse_int(item.get("sp_stock_lmp_irds_cnt", "0"))
                executive_name = item.get("repror", "")
                position = item.get("isu_exctv_ofcps", "")

                if change_count > 0:
                    net_buy_executives.append(f"{executive_name}({position})")
                    # CEO 매수 확인
                    if any(p in position for p in ["대표", "사장", "회장", "CEO"]):
                        ceo_bought = True
                elif change_count < 0:
                    net_sell_count += 1

            net_buy_count = len(net_buy_executives)

            if ceo_bought or net_buy_count >= 2:
                signal = SignalType.STRONG_BUY
                signal_desc = f"최근 6개월간 {net_buy_count}명의 임원이 순매수했습니다. 강력한 호재!"
            elif net_buy_count >= 1:
                signal = SignalType.BUY
                signal_desc = f"최근 6개월간 {net_buy_count}명의 임원이 순매수했습니다."
            elif net_sell_count > net_buy_count:
                signal = SignalType.SELL
                signal_desc = f"매도가 매수보다 많습니다. ({net_sell_count}건 매도)"
            else:
                signal = SignalType.HOLD
                signal_desc = "특별한 내부자 거래 신호가 없습니다."

            return InsiderTradingIndicator(
                name="임원/주요주주 순매수 강도",
                description="최근 6개월 내 임원 장내매수 현황",
                signal=signal,
                signal_description=signal_desc,
                net_buy_count=net_buy_count,
                net_buy_executives=net_buy_executives[:10],  # 최대 10명
                net_sell_count=net_sell_count,
                ceo_bought=ceo_bought,
            )

        except Exception as e:
            print(f"Error calculating insider trading: {e}")
            return None

    async def get_comprehensive_analysis(
        self, corp_code: str, corp_name: str, bsns_year: str, fs_div: str = "OFS"
    ) -> ComprehensiveAnalysis:
        """종합 분석 수행"""
        # 5대 지표 계산
        cash_generation = await self.calculate_cash_generation(corp_code, bsns_year, fs_div)
        interest_coverage = await self.calculate_interest_coverage(corp_code, bsns_year, fs_div)
        operating_growth = await self.calculate_operating_profit_growth(corp_code, bsns_year, fs_div)
        dilution_risk = await self.calculate_dilution_risk(corp_code, bsns_year)
        insider_trading = await self.calculate_insider_trading(corp_code)

        # 점수 계산 (각 지표 20점)
        score = 0
        indicator_count = 0

        signal_scores = {
            SignalType.STRONG_BUY: 20,
            SignalType.BUY: 15,
            SignalType.HOLD: 10,
            SignalType.CAUTION: 5,
            SignalType.SELL: 2,
            SignalType.STRONG_SELL: 0,
        }

        for indicator in [cash_generation, interest_coverage, operating_growth, dilution_risk, insider_trading]:
            if indicator:
                score += signal_scores.get(indicator.signal, 10)
                indicator_count += 1

        overall_score = (score / (indicator_count * 20) * 100) if indicator_count > 0 else 0

        # 종합 신호 결정
        if overall_score >= 80:
            overall_signal = SignalType.STRONG_BUY
            recommendation = "적극 매수 추천. 모든 지표가 우수합니다."
        elif overall_score >= 60:
            overall_signal = SignalType.BUY
            recommendation = "매수 고려. 대부분의 지표가 양호합니다."
        elif overall_score >= 40:
            overall_signal = SignalType.HOLD
            recommendation = "관망 추천. 일부 지표에 주의가 필요합니다."
        elif overall_score >= 20:
            overall_signal = SignalType.SELL
            recommendation = "매도 고려. 여러 지표에서 경고 신호가 나타납니다."
        else:
            overall_signal = SignalType.STRONG_SELL
            recommendation = "즉시 매도 권고. 심각한 문제가 감지됩니다."

        return ComprehensiveAnalysis(
            corp_code=corp_code,
            corp_name=corp_name,
            analysis_date=datetime.now().strftime("%Y-%m-%d"),
            bsns_year=bsns_year,
            cash_generation=cash_generation,
            interest_coverage=interest_coverage,
            operating_profit_growth=operating_growth,
            dilution_risk=dilution_risk,
            insider_trading=insider_trading,
            overall_score=overall_score,
            overall_signal=overall_signal,
            recommendation=recommendation,
        )


# 싱글톤 인스턴스
indicator_service = IndicatorService()
