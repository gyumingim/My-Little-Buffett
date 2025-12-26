"""
버핏형 텐배거 채점 알고리즘

워런 버핏의 가치투자 원칙 기반:
1. 필터링 단계: 부적격 기업 제외 (좀비 기업 걸러내기)
2. 스코어링 단계: 100점 만점 채점

점수 배분:
- 수익성의 지속성 (ROE): 30점
- 현금 창출 능력: 25점
- 성장성 및 해자: 20점
- 재무 안정성: 15점
- 현금흐름 질: 10점
"""

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

    # 현금흐름표 (CF)
    operating_cash_flow: float = 0  # 영업활동 현금흐름
    investing_cash_flow: float = 0  # 투자활동 현금흐름
    financing_cash_flow: float = 0  # 재무활동 현금흐름


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
        account_id = item.get("account_id", "") or ""
        account_nm = item.get("account_nm", "") or ""
        amount = parse_amount(item.get(amount_key))

        # account_id에서 ifrs- 또는 ifrs_full_ prefix 처리
        account_id_lower = account_id.lower()

        # 손익계산서 (IS)
        if sj_div == "IS":
            if "revenue" in account_id_lower or "매출액" in account_nm or account_nm == "수익(매출액)":
                m.revenue = max(m.revenue, amount)
            elif "costofsales" in account_id_lower or "매출원가" in account_nm:
                m.cost_of_sales = max(m.cost_of_sales, amount)
            elif "grossprofit" in account_id_lower or "매출총이익" in account_nm:
                m.gross_profit = max(m.gross_profit, amount)
            elif "operatingincome" in account_id_lower or "영업이익" in account_nm or "영업손익" in account_nm:
                m.operating_income = max(m.operating_income, amount)
            elif "금융비용" in account_nm or "이자비용" in account_nm or "financecost" in account_id_lower:
                m.finance_cost = max(m.finance_cost, amount)
            elif "profitloss" in account_id_lower or "당기순이익" in account_nm or "당기순손익" in account_nm or account_nm == "분기순이익":
                m.net_income = max(m.net_income, amount)

        # 재무상태표 (BS)
        elif sj_div == "BS":
            # 자산총계
            if "assets" in account_id_lower and "current" not in account_id_lower:
                m.total_assets = max(m.total_assets, amount)
            elif "자산총계" in account_nm or account_nm == "자산":
                m.total_assets = max(m.total_assets, amount)
            # 유동자산
            elif "currentassets" in account_id_lower or "유동자산" in account_nm:
                m.current_assets = max(m.current_assets, amount)
            # 부채총계
            elif "liabilities" in account_id_lower and "current" not in account_id_lower:
                m.total_liabilities = max(m.total_liabilities, amount)
            elif "부채총계" in account_nm or account_nm == "부채":
                m.total_liabilities = max(m.total_liabilities, amount)
            # 유동부채
            elif "currentliabilities" in account_id_lower or "유동부채" in account_nm:
                m.current_liabilities = max(m.current_liabilities, amount)
            # 자본총계 (다양한 형태 처리)
            elif "equity" in account_id_lower and "retained" not in account_id_lower:
                m.total_equity = max(m.total_equity, amount)
            elif "자본총계" in account_nm or "자본 총계" in account_nm:
                m.total_equity = max(m.total_equity, amount)
            elif account_nm == "자본" or account_nm == "자본계":
                m.total_equity = max(m.total_equity, amount)
            elif "지배기업" in account_nm and "지분" in account_nm:
                m.total_equity = max(m.total_equity, amount)
            # 이익잉여금
            elif "retainedearnings" in account_id_lower or "이익잉여금" in account_nm:
                m.retained_earnings = max(m.retained_earnings, amount)

        # 현금흐름표 (CF)
        elif sj_div == "CF":
            if "operating" in account_id_lower or "영업활동" in account_nm:
                m.operating_cash_flow = amount
            elif "investing" in account_id_lower or "투자활동" in account_nm:
                m.investing_cash_flow = amount
            elif "financing" in account_id_lower or "재무활동" in account_nm:
                m.financing_cash_flow = amount

    return m


@dataclass
class Indicator:
    """개별 지표"""
    name: str
    value: float
    score: float  # 0-100 (해당 항목 만점 기준)
    max_score: float  # 해당 항목 최대 점수
    grade: str  # A/B/C/D/F
    description: str
    good_criteria: str
    category: str  # 수익성/안정성/성장성/현금흐름


@dataclass
class FilterResult:
    """필터링 결과"""
    passed: bool
    failed_reasons: list[str]


@dataclass
class AnalysisResult:
    """종합 분석 결과"""
    corp_code: str
    corp_name: str
    year: str
    fs_div: str
    indicators: list[Indicator]
    total_score: float  # 0-100
    signal: str  # 강력매수/매수/관망/매도/강력매도
    recommendation: str
    filter_result: FilterResult
    metrics: dict


class BuffettAnalyzer:
    """버핏형 가치투자 분석기"""

    async def analyze(self, corp_code: str, corp_name: str, year: str, fs_div: str = "CFS") -> AnalysisResult | None:
        """종합 분석 수행"""
        # 재무제표 조회
        data = await dart_client.get_financial_statements(
            corp_code=corp_code, bsns_year=year, reprt_code="11011", fs_div=fs_div
        )

        if data.get("status") != "000":
            return None

        statements = data.get("list", [])
        if not statements:
            return None

        # 3개년 지표 추출
        current = extract_metrics(statements, "thstrm")
        previous = extract_metrics(statements, "frmtrm")
        before_prev = extract_metrics(statements, "bfefrmtrm")

        # ========================================
        # 1단계: 필터링 (부적격 기업 제외)
        # ========================================
        filter_result = self._apply_filters(current, previous)

        # ========================================
        # 2단계: 버핏형 채점 (100점 만점)
        # ========================================
        indicators = []

        # (1) 수익성의 지속성 - ROE (30점)
        roe_indicator = self._calc_roe_buffett(current, previous, before_prev)
        indicators.append(roe_indicator)

        # (2) 현금 창출 능력 - PCR (25점)
        pcr_indicator = self._calc_cash_generation_buffett(current)
        indicators.append(pcr_indicator)

        # (3) 성장성 및 해자 - 영업이익 성장률 (20점)
        growth_indicator = self._calc_growth_buffett(current, previous)
        indicators.append(growth_indicator)

        # (4) 재무 안정성 - 이자보상배율 (15점)
        safety_indicator = self._calc_interest_coverage_buffett(current)
        indicators.append(safety_indicator)

        # (5) 현금흐름 질 - 영업CF/순이익 (10점)
        cfq_indicator = self._calc_cashflow_quality_buffett(current)
        indicators.append(cfq_indicator)

        # 필터 통과 못하면 0점
        if not filter_result.passed:
            total_score = 0.0
        else:
            total_score = sum(ind.score for ind in indicators)

        # 신호 결정
        signal, recommendation = self._get_signal(total_score, filter_result)

        return AnalysisResult(
            corp_code=corp_code,
            corp_name=corp_name,
            year=year,
            fs_div=fs_div,
            indicators=indicators,
            total_score=round(total_score, 1),
            signal=signal,
            recommendation=recommendation,
            filter_result=filter_result,
            metrics={
                "current": current.__dict__,
                "previous": previous.__dict__,
            }
        )

    def _apply_filters(self, current: FinancialMetrics, previous: FinancialMetrics) -> FilterResult:
        """필터링 단계: 좀비 기업 걸러내기"""
        failed_reasons = []

        # 필터 1: 이자보상배율 < 1.0 (이자도 못 갚는 기업)
        if current.finance_cost > 0:
            interest_coverage = current.operating_income / current.finance_cost
            if interest_coverage < 1.0:
                failed_reasons.append(f"이자보상배율 {interest_coverage:.1f}배 (1.0 미만 - 이자도 못 갚음)")

        # 필터 2: 2년 연속 영업CF < 순이익 (이익의 질 낮음)
        if current.net_income > 0 and previous.net_income > 0:
            curr_cfq = current.operating_cash_flow / current.net_income if current.net_income > 0 else 0
            prev_cfq = previous.operating_cash_flow / previous.net_income if previous.net_income > 0 else 0
            if curr_cfq < 1.0 and prev_cfq < 1.0:
                failed_reasons.append(f"2년 연속 현금흐름 질 낮음 (영업CF < 순이익)")

        # 필터 3: 자본잠식 (자본총계 <= 0)
        if current.total_equity <= 0:
            failed_reasons.append("자본잠식 상태")

        # 필터 4: 2년 연속 적자
        if current.net_income < 0 and previous.net_income < 0:
            failed_reasons.append("2년 연속 적자")

        return FilterResult(
            passed=len(failed_reasons) == 0,
            failed_reasons=failed_reasons
        )

    def _calc_roe_buffett(self, curr: FinancialMetrics, prev: FinancialMetrics, bprev: FinancialMetrics) -> Indicator:
        """
        ROE (자기자본이익률) - 30점 만점
        버핏 기준: 지속적으로 15% 이상
        """
        max_score = 30

        if curr.total_equity <= 0:
            return Indicator("ROE (자기자본이익률)", 0, 0, max_score, "F",
                           "자본잠식", "15% 이상 지속", "수익성")

        roe = (curr.net_income / curr.total_equity) * 100

        # 버핏 기준 채점
        if roe >= 20:
            score = 30  # 탁월
        elif roe >= 15:
            score = 25  # 우수 (버핏 기준)
        elif roe >= 10:
            score = 15  # 양호
        elif roe >= 5:
            score = 8   # 보통
        elif roe >= 0:
            score = 3   # 미흡
        else:
            score = 0   # 적자

        grade = self._score_to_grade(score, max_score)

        return Indicator(
            name="ROE (자기자본이익률)",
            value=round(roe, 1),
            score=score,
            max_score=max_score,
            grade=grade,
            description=f"자본 대비 {roe:.1f}% 수익 창출" if roe > 0 else "적자 상태",
            good_criteria="15% 이상 지속 (버핏 기준)",
            category="수익성"
        )

    def _calc_cash_generation_buffett(self, m: FinancialMetrics) -> Indicator:
        """
        현금 창출 능력 (영업CF/순이익) - 25점 만점
        버핏 기준: 1.2 이상이면 우수
        """
        max_score = 25

        if m.net_income <= 0:
            if m.operating_cash_flow > 0:
                return Indicator("현금창출력 (OCF/NI)", 999, 25, max_score, "A",
                               "적자에도 현금 창출", "1.2 이상", "현금창출")
            return Indicator("현금창출력 (OCF/NI)", 0, 0, max_score, "F",
                           "적자 + 현금흐름 부정적", "1.2 이상", "현금창출")

        ratio = m.operating_cash_flow / m.net_income

        if ratio >= 1.5:
            score = 25  # 탁월
        elif ratio >= 1.2:
            score = 22  # 우수 (버핏 기준)
        elif ratio >= 1.0:
            score = 15  # 양호
        elif ratio >= 0.7:
            score = 8   # 보통
        elif ratio >= 0.5:
            score = 4   # 미흡
        else:
            score = 0   # 위험

        grade = self._score_to_grade(score, max_score)

        return Indicator(
            name="현금창출력 (OCF/NI)",
            value=round(ratio, 2),
            score=score,
            max_score=max_score,
            grade=grade,
            description=f"순이익 대비 {ratio:.2f}배 현금 창출",
            good_criteria="1.2 이상 (이익보다 현금이 많이 들어옴)",
            category="현금창출"
        )

    def _calc_growth_buffett(self, curr: FinancialMetrics, prev: FinancialMetrics) -> Indicator:
        """
        영업이익 성장률 - 20점 만점
        버핏 기준: 15% 이상 고성장
        """
        max_score = 20

        if prev.operating_income <= 0:
            if curr.operating_income > 0:
                return Indicator("영업이익 성장률", 100, 20, max_score, "A",
                               "흑자 전환 성공", "15% 이상 성장", "성장성")
            return Indicator("영업이익 성장률", 0, 0, max_score, "F",
                           "적자 지속", "15% 이상 성장", "성장성")

        growth = ((curr.operating_income - prev.operating_income) / abs(prev.operating_income)) * 100

        if growth >= 30:
            score = 20  # 탁월
        elif growth >= 15:
            score = 18  # 고성장 (버핏 기준)
        elif growth >= 5:
            score = 12  # 안정적 성장
        elif growth >= 0:
            score = 6   # 보합
        elif growth >= -15:
            score = 2   # 역성장
        else:
            score = 0   # 급감

        grade = self._score_to_grade(score, max_score)
        trend = "성장" if growth > 0 else ("감소" if growth < 0 else "유지")

        return Indicator(
            name="영업이익 성장률",
            value=round(growth, 1),
            score=score,
            max_score=max_score,
            grade=grade,
            description=f"전년 대비 {growth:+.1f}% {trend}",
            good_criteria="15% 이상 고성장",
            category="성장성"
        )

    def _calc_interest_coverage_buffett(self, m: FinancialMetrics) -> Indicator:
        """
        이자보상배율 - 15점 만점
        버핏 기준: 3배 이상 안전
        """
        max_score = 15

        if m.finance_cost <= 0:
            if m.operating_income > 0:
                return Indicator("이자보상배율", 999, 15, max_score, "A",
                               "무차입 또는 이자비용 없음", "3배 이상", "안정성")
            return Indicator("이자보상배율", 0, 8, max_score, "B",
                           "영업이익 없지만 이자부담도 없음", "3배 이상", "안정성")

        ratio = m.operating_income / m.finance_cost

        if ratio >= 5.0:
            score = 15  # 매우 안전
        elif ratio >= 3.0:
            score = 12  # 안전 (버핏 기준)
        elif ratio >= 1.5:
            score = 7   # 보통
        elif ratio >= 1.0:
            score = 3   # 위험
        else:
            score = 0   # 매우 위험 (이자도 못 갚음)

        grade = self._score_to_grade(score, max_score)

        return Indicator(
            name="이자보상배율",
            value=round(ratio, 1),
            score=score,
            max_score=max_score,
            grade=grade,
            description=f"영업이익이 이자비용의 {ratio:.1f}배",
            good_criteria="3배 이상 안전, 1배 미만 위험",
            category="안정성"
        )

    def _calc_cashflow_quality_buffett(self, m: FinancialMetrics) -> Indicator:
        """
        현금흐름 질 (부채비율 연계) - 10점 만점
        """
        max_score = 10

        if m.total_equity <= 0:
            return Indicator("부채비율", 999, 0, max_score, "F",
                           "자본잠식", "100% 이하", "안정성")

        debt_ratio = (m.total_liabilities / m.total_equity) * 100

        if debt_ratio <= 50:
            score = 10  # 매우 건전
        elif debt_ratio <= 100:
            score = 8   # 건전
        elif debt_ratio <= 150:
            score = 5   # 보통
        elif debt_ratio <= 200:
            score = 2   # 높음
        else:
            score = 0   # 위험

        grade = self._score_to_grade(score, max_score)

        return Indicator(
            name="부채비율",
            value=round(debt_ratio, 1),
            score=score,
            max_score=max_score,
            grade=grade,
            description=f"자본 대비 부채 {debt_ratio:.1f}%",
            good_criteria="100% 이하 건전, 50% 이하 우수",
            category="안정성"
        )

    def _score_to_grade(self, score: float, max_score: float) -> str:
        """점수를 등급으로 변환"""
        ratio = score / max_score if max_score > 0 else 0
        if ratio >= 0.8:
            return "A"
        elif ratio >= 0.6:
            return "B"
        elif ratio >= 0.4:
            return "C"
        elif ratio >= 0.2:
            return "D"
        return "F"

    def _get_signal(self, total_score: float, filter_result: FilterResult) -> tuple[str, str]:
        """매매 신호 결정"""
        if not filter_result.passed:
            reasons = ", ".join(filter_result.failed_reasons[:2])
            return "투자부적격", f"필터링 탈락: {reasons}"

        if total_score >= 80:
            return "강력매수", "모든 지표가 버핏 기준을 충족합니다. 장기 투자 적합."
        elif total_score >= 65:
            return "매수", "대부분의 지표가 우수합니다. 투자 검토 권장."
        elif total_score >= 50:
            return "관망", "일부 지표가 부족합니다. 신중한 검토 필요."
        elif total_score >= 35:
            return "매도", "여러 지표가 부정적입니다. 투자 주의."
        else:
            return "강력매도", "대부분의 지표가 미달입니다. 투자 회피 권고."


# 싱글톤
financial_analyzer = BuffettAnalyzer()
