"""종합 투자 분석 서비스 (재무제표 기반 10개 지표)"""

from datetime import datetime
from dataclasses import dataclass
from shared.api.dart_client import dart_client


@dataclass
class FinancialMetrics:
    """재무제표에서 추출한 핵심 수치"""
    # 손익계산서 (IS)
    revenue: float = 0  # 매출액
    cost_of_sales: float = 0  # 매출원가
    gross_profit: float = 0  # 매출총이익
    operating_income: float = 0  # 영업이익
    finance_cost: float = 0  # 금융비용 (이자비용)
    net_income: float = 0  # 당기순이익

    # 재무상태표 (BS)
    total_assets: float = 0  # 자산총계
    current_assets: float = 0  # 유동자산
    total_liabilities: float = 0  # 부채총계
    current_liabilities: float = 0  # 유동부채
    total_equity: float = 0  # 자본총계
    retained_earnings: float = 0  # 이익잉여금
    short_term_borrowings: float = 0  # 단기차입금
    bonds: float = 0  # 사채

    # 현금흐름표 (CF)
    operating_cash_flow: float = 0  # 영업활동 현금흐름
    investing_cash_flow: float = 0  # 투자활동 현금흐름
    financing_cash_flow: float = 0  # 재무활동 현금흐름
    interest_paid: float = 0  # 이자의 지급
    capex: float = 0  # 유형자산 취득


@dataclass
class YearMetrics:
    """연도별 재무 지표"""
    year: str
    current: FinancialMetrics  # 당기
    previous: FinancialMetrics | None = None  # 전기
    before_previous: FinancialMetrics | None = None  # 전전기


def parse_amount(value: str | None) -> float:
    """금액 문자열을 숫자로 변환"""
    if not value or value == "":
        return 0.0
    try:
        return float(value.replace(",", ""))
    except:
        return 0.0


def extract_metrics(statements: list, term: str = "thstrm") -> FinancialMetrics:
    """재무제표에서 지표 추출 (term: thstrm=당기, frmtrm=전기, bfefrmtrm=전전기)"""
    m = FinancialMetrics()
    amount_key = f"{term}_amount"

    for item in statements:
        sj_div = item.get("sj_div", "")
        account_id = item.get("account_id", "")
        account_nm = item.get("account_nm", "")
        amount = parse_amount(item.get(amount_key))

        # 손익계산서 (IS)
        if sj_div == "IS":
            if account_id == "ifrs_Revenue" or "매출액" in account_nm:
                m.revenue = max(m.revenue, amount)
            elif account_id == "ifrs_CostOfSales":
                m.cost_of_sales = amount
            elif account_id == "ifrs_GrossProfit":
                m.gross_profit = amount
            elif account_id == "dart_OperatingIncomeLoss" or "영업이익" in account_nm:
                m.operating_income = max(m.operating_income, amount)
            elif "금융비용" in account_nm:
                m.finance_cost = amount
            elif account_id == "ifrs_ProfitLoss" or "당기순이익" in account_nm:
                m.net_income = max(m.net_income, amount)

        # 재무상태표 (BS)
        elif sj_div == "BS":
            if account_id == "ifrs_Assets":
                m.total_assets = amount
            elif account_id == "ifrs_CurrentAssets":
                m.current_assets = amount
            elif account_id == "ifrs_Liabilities":
                m.total_liabilities = amount
            elif account_id == "ifrs_CurrentLiabilities":
                m.current_liabilities = amount
            elif account_id == "ifrs_Equity":
                m.total_equity = amount
            elif account_id == "ifrs_RetainedEarnings":
                m.retained_earnings = amount
            elif account_id == "ifrs_ShorttermBorrowings" or "단기차입금" in account_nm:
                m.short_term_borrowings = amount
            elif account_id == "dart_BondsIssued" or account_nm == "사채":
                m.bonds = amount

        # 현금흐름표 (CF)
        elif sj_div == "CF":
            if account_id == "ifrs_CashFlowsFromUsedInOperatingActivities":
                m.operating_cash_flow = amount
            elif account_id == "ifrs_CashFlowsFromUsedInInvestingActivities":
                m.investing_cash_flow = amount
            elif account_id == "ifrs_CashFlowsFromUsedInFinancingActivities":
                m.financing_cash_flow = amount
            elif "이자의 지급" in account_nm:
                m.interest_paid = amount
            elif "유형자산의 취득" in account_nm:
                m.capex = abs(amount)

    return m


@dataclass
class Indicator:
    """개별 지표"""
    name: str
    value: float
    score: float  # 0-100
    grade: str  # A/B/C/D/F
    description: str
    good_criteria: str  # 좋은 기준 설명
    trend: str = ""  # 상승/하락/유지


@dataclass
class AnalysisResult:
    """종합 분석 결과"""
    corp_code: str
    corp_name: str
    year: str
    indicators: list[Indicator]
    total_score: float  # 0-100
    signal: str  # 강력매수/매수/관망/매도/강력매도
    recommendation: str
    metrics: dict  # 원본 수치


class FinancialAnalyzer:
    """재무제표 기반 종합 분석"""

    async def analyze(self, corp_code: str, corp_name: str, year: str, fs_div: str = "OFS") -> AnalysisResult | None:
        """종합 분석 수행"""
        # 재무제표 조회
        data = await dart_client.get_financial_statements(
            corp_code=corp_code, bsns_year=year, reprt_code="11011", fs_div=fs_div
        )

        if data.get("status") != "000":
            return None

        statements = data.get("list", [])

        # 3개년 지표 추출
        current = extract_metrics(statements, "thstrm")
        previous = extract_metrics(statements, "frmtrm")
        before_prev = extract_metrics(statements, "bfefrmtrm")

        # 10개 지표 계산
        indicators = []

        # 1. 수익성 지표
        indicators.append(self._calc_roe(current))
        indicators.append(self._calc_operating_margin(current))
        indicators.append(self._calc_net_margin(current))

        # 2. 안정성 지표
        indicators.append(self._calc_debt_ratio(current))
        indicators.append(self._calc_interest_coverage(current))
        indicators.append(self._calc_current_ratio(current))

        # 3. 성장성 지표
        indicators.append(self._calc_revenue_growth(current, previous))
        indicators.append(self._calc_operating_growth(current, previous))
        indicators.append(self._calc_net_income_growth(current, previous))

        # 4. 현금흐름 지표
        indicators.append(self._calc_cash_flow_quality(current))

        # 종합 점수 계산 (가중 평균)
        weights = [15, 10, 10, 10, 15, 5, 10, 10, 5, 10]  # 총 100
        total_score = sum(ind.score * w / 100 for ind, w in zip(indicators, weights))

        # 신호 결정
        if total_score >= 80:
            signal = "강력매수"
            recommendation = "모든 재무지표가 우수합니다. 장기 투자 적합."
        elif total_score >= 65:
            signal = "매수"
            recommendation = "대부분의 지표가 양호합니다. 투자 고려."
        elif total_score >= 50:
            signal = "관망"
            recommendation = "일부 지표에 주의가 필요합니다."
        elif total_score >= 35:
            signal = "매도"
            recommendation = "여러 지표가 부정적입니다. 신중한 접근 필요."
        else:
            signal = "강력매도"
            recommendation = "재무 상태가 좋지 않습니다. 투자 회피 권고."

        return AnalysisResult(
            corp_code=corp_code,
            corp_name=corp_name,
            year=year,
            indicators=indicators,
            total_score=round(total_score, 1),
            signal=signal,
            recommendation=recommendation,
            metrics={
                "current": current.__dict__,
                "previous": previous.__dict__,
            }
        )

    def _calc_roe(self, m: FinancialMetrics) -> Indicator:
        """ROE (자기자본이익률) = 당기순이익 / 자본총계 × 100"""
        if m.total_equity <= 0:
            return Indicator("ROE", 0, 0, "F", "자본잠식 상태", "15% 이상이 우수")

        value = (m.net_income / m.total_equity) * 100

        if value >= 20:
            score, grade = 100, "A"
        elif value >= 15:
            score, grade = 85, "A"
        elif value >= 10:
            score, grade = 70, "B"
        elif value >= 5:
            score, grade = 50, "C"
        elif value >= 0:
            score, grade = 30, "D"
        else:
            score, grade = 0, "F"

        return Indicator(
            name="ROE (자기자본이익률)",
            value=round(value, 1),
            score=score,
            grade=grade,
            description=f"자본 대비 {value:.1f}% 수익 창출",
            good_criteria="15% 이상 우수, 10% 이상 양호"
        )

    def _calc_operating_margin(self, m: FinancialMetrics) -> Indicator:
        """영업이익률 = 영업이익 / 매출액 × 100"""
        if m.revenue <= 0:
            return Indicator("영업이익률", 0, 0, "F", "매출 없음", "10% 이상이 양호")

        value = (m.operating_income / m.revenue) * 100

        if value >= 20:
            score, grade = 100, "A"
        elif value >= 15:
            score, grade = 85, "A"
        elif value >= 10:
            score, grade = 70, "B"
        elif value >= 5:
            score, grade = 50, "C"
        elif value >= 0:
            score, grade = 30, "D"
        else:
            score, grade = 0, "F"

        return Indicator(
            name="영업이익률",
            value=round(value, 1),
            score=score,
            grade=grade,
            description=f"매출 대비 {value:.1f}% 영업이익",
            good_criteria="15% 이상 우수, 10% 이상 양호"
        )

    def _calc_net_margin(self, m: FinancialMetrics) -> Indicator:
        """순이익률 = 당기순이익 / 매출액 × 100"""
        if m.revenue <= 0:
            return Indicator("순이익률", 0, 0, "F", "매출 없음", "7% 이상이 양호")

        value = (m.net_income / m.revenue) * 100

        if value >= 15:
            score, grade = 100, "A"
        elif value >= 10:
            score, grade = 85, "A"
        elif value >= 7:
            score, grade = 70, "B"
        elif value >= 3:
            score, grade = 50, "C"
        elif value >= 0:
            score, grade = 30, "D"
        else:
            score, grade = 0, "F"

        return Indicator(
            name="순이익률",
            value=round(value, 1),
            score=score,
            grade=grade,
            description=f"매출 대비 {value:.1f}% 순이익",
            good_criteria="10% 이상 우수, 7% 이상 양호"
        )

    def _calc_debt_ratio(self, m: FinancialMetrics) -> Indicator:
        """부채비율 = 부채총계 / 자본총계 × 100"""
        if m.total_equity <= 0:
            return Indicator("부채비율", 999, 0, "F", "자본잠식", "100% 이하가 안전")

        value = (m.total_liabilities / m.total_equity) * 100

        if value <= 50:
            score, grade = 100, "A"
        elif value <= 100:
            score, grade = 80, "B"
        elif value <= 150:
            score, grade = 60, "C"
        elif value <= 200:
            score, grade = 40, "D"
        else:
            score, grade = 20, "F"

        return Indicator(
            name="부채비율",
            value=round(value, 1),
            score=score,
            grade=grade,
            description=f"자본 대비 부채 {value:.1f}%",
            good_criteria="100% 이하 안전, 50% 이하 우수"
        )

    def _calc_interest_coverage(self, m: FinancialMetrics) -> Indicator:
        """이자보상배율 = 영업이익 / 금융비용"""
        interest = m.finance_cost if m.finance_cost > 0 else m.interest_paid

        if interest <= 0:
            if m.operating_income > 0:
                return Indicator("이자보상배율", 999, 100, "A", "무차입 경영", "3배 이상이 안전")
            else:
                return Indicator("이자보상배율", 0, 50, "C", "영업이익 없음", "3배 이상이 안전")

        value = m.operating_income / interest

        if value >= 5:
            score, grade = 100, "A"
        elif value >= 3:
            score, grade = 85, "A"
        elif value >= 2:
            score, grade = 65, "B"
        elif value >= 1:
            score, grade = 40, "C"
        elif value >= 0:
            score, grade = 20, "D"
        else:
            score, grade = 0, "F"

        return Indicator(
            name="이자보상배율",
            value=round(value, 1),
            score=score,
            grade=grade,
            description=f"영업이익이 이자비용의 {value:.1f}배",
            good_criteria="3배 이상 안전, 1배 미만 위험"
        )

    def _calc_current_ratio(self, m: FinancialMetrics) -> Indicator:
        """유동비율 = 유동자산 / 유동부채 × 100"""
        if m.current_liabilities <= 0:
            return Indicator("유동비율", 999, 100, "A", "단기부채 없음", "150% 이상이 안전")

        value = (m.current_assets / m.current_liabilities) * 100

        if value >= 200:
            score, grade = 100, "A"
        elif value >= 150:
            score, grade = 80, "B"
        elif value >= 100:
            score, grade = 60, "C"
        elif value >= 80:
            score, grade = 40, "D"
        else:
            score, grade = 20, "F"

        return Indicator(
            name="유동비율",
            value=round(value, 1),
            score=score,
            grade=grade,
            description=f"단기채무 대비 {value:.1f}% 유동자산 보유",
            good_criteria="150% 이상 안전, 100% 미만 위험"
        )

    def _calc_revenue_growth(self, current: FinancialMetrics, prev: FinancialMetrics) -> Indicator:
        """매출 성장률 = (당기 - 전기) / 전기 × 100"""
        if prev.revenue <= 0:
            return Indicator("매출성장률", 0, 50, "C", "전기 데이터 없음", "10% 이상 성장이 양호")

        value = ((current.revenue - prev.revenue) / prev.revenue) * 100

        if value >= 20:
            score, grade = 100, "A"
        elif value >= 10:
            score, grade = 80, "B"
        elif value >= 5:
            score, grade = 65, "C"
        elif value >= 0:
            score, grade = 45, "C"
        elif value >= -10:
            score, grade = 30, "D"
        else:
            score, grade = 10, "F"

        trend = "↑ 성장" if value > 0 else ("↓ 역성장" if value < 0 else "→ 유지")

        return Indicator(
            name="매출성장률",
            value=round(value, 1),
            score=score,
            grade=grade,
            description=f"전년 대비 {value:+.1f}% {trend}",
            good_criteria="10% 이상 고성장, 0% 이상 양호",
            trend=trend
        )

    def _calc_operating_growth(self, current: FinancialMetrics, prev: FinancialMetrics) -> Indicator:
        """영업이익 성장률"""
        if prev.operating_income <= 0:
            if current.operating_income > 0:
                return Indicator("영업이익성장률", 100, 100, "A", "흑자 전환", "15% 이상이 고성장")
            return Indicator("영업이익성장률", 0, 30, "D", "적자 지속", "15% 이상이 고성장")

        value = ((current.operating_income - prev.operating_income) / abs(prev.operating_income)) * 100

        if value >= 30:
            score, grade = 100, "A"
        elif value >= 15:
            score, grade = 85, "A"
        elif value >= 5:
            score, grade = 65, "B"
        elif value >= 0:
            score, grade = 50, "C"
        elif value >= -15:
            score, grade = 30, "D"
        else:
            score, grade = 10, "F"

        trend = "↑ 성장" if value > 0 else ("↓ 감소" if value < 0 else "→ 유지")

        return Indicator(
            name="영업이익성장률",
            value=round(value, 1),
            score=score,
            grade=grade,
            description=f"전년 대비 {value:+.1f}% {trend}",
            good_criteria="15% 이상 고성장, 0% 이상 양호",
            trend=trend
        )

    def _calc_net_income_growth(self, current: FinancialMetrics, prev: FinancialMetrics) -> Indicator:
        """순이익 성장률"""
        if prev.net_income <= 0:
            if current.net_income > 0:
                return Indicator("순이익성장률", 100, 100, "A", "흑자 전환", "15% 이상이 고성장")
            return Indicator("순이익성장률", 0, 20, "F", "적자 지속", "15% 이상이 고성장")

        value = ((current.net_income - prev.net_income) / abs(prev.net_income)) * 100

        if value >= 30:
            score, grade = 100, "A"
        elif value >= 15:
            score, grade = 80, "A"
        elif value >= 5:
            score, grade = 65, "B"
        elif value >= 0:
            score, grade = 50, "C"
        elif value >= -15:
            score, grade = 30, "D"
        else:
            score, grade = 10, "F"

        trend = "↑ 성장" if value > 0 else ("↓ 감소" if value < 0 else "→ 유지")

        return Indicator(
            name="순이익성장률",
            value=round(value, 1),
            score=score,
            grade=grade,
            description=f"전년 대비 {value:+.1f}% {trend}",
            good_criteria="15% 이상 고성장, 0% 이상 양호",
            trend=trend
        )

    def _calc_cash_flow_quality(self, m: FinancialMetrics) -> Indicator:
        """현금흐름 질 = 영업CF / 순이익 (버핏 기준: >1)"""
        if m.net_income <= 0:
            if m.operating_cash_flow > 0:
                return Indicator("현금흐름질", 999, 100, "A", "적자에도 현금창출", "1.0 이상이 우수")
            return Indicator("현금흐름질", 0, 20, "F", "현금흐름 부정적", "1.0 이상이 우수")

        value = m.operating_cash_flow / m.net_income

        if value >= 1.5:
            score, grade = 100, "A"
        elif value >= 1.0:
            score, grade = 85, "A"
        elif value >= 0.8:
            score, grade = 65, "B"
        elif value >= 0.5:
            score, grade = 45, "C"
        elif value >= 0:
            score, grade = 25, "D"
        else:
            score, grade = 0, "F"

        return Indicator(
            name="현금흐름질 (버핏지표)",
            value=round(value, 2),
            score=score,
            grade=grade,
            description=f"순이익 대비 {value:.2f}배 현금 창출",
            good_criteria="1.0 이상 우수 (실제 현금이 들어옴)"
        )


# 싱글톤
financial_analyzer = FinancialAnalyzer()
