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
    cash_and_equivalents: float = 0  # 현금및현금성자산
    total_liabilities: float = 0  # 부채총계
    current_liabilities: float = 0  # 유동부채
    total_equity: float = 0  # 자본총계
    capital_stock: float = 0  # 자본금
    retained_earnings: float = 0  # 이익잉여금

    # 현금흐름표 (CF)
    operating_cash_flow: float = 0  # 영업활동 현금흐름
    investing_cash_flow: float = 0  # 투자활동 현금흐름
    financing_cash_flow: float = 0  # 재무활동 현금흐름

    # 계산된 비율 (편의용)
    @property
    def operating_margin(self) -> float:
        """영업이익률 = 영업이익 / 매출액"""
        return (self.operating_income / self.revenue * 100) if self.revenue > 0 else 0

    @property
    def roe(self) -> float:
        """ROE = 순이익 / 자본총계"""
        return (self.net_income / self.total_equity * 100) if self.total_equity > 0 else 0

    @property
    def roic(self) -> float:
        """ROIC = 세후영업이익 / 투하자본 (근사치)"""
        # 세후영업이익 ≈ 영업이익 * 0.75 (법인세 25% 가정)
        nopat = self.operating_income * 0.75
        # 투하자본 = 자본총계 + 유이자부채 - 현금성자산
        # 유이자부채 ≈ 총부채 - 유동부채의 일부 (단순화)
        invested_capital = self.total_equity + (self.total_liabilities * 0.5) - self.cash_and_equivalents
        return (nopat / invested_capital * 100) if invested_capital > 0 else 0

    @property
    def debt_ratio(self) -> float:
        """부채비율 = 부채총계 / 자본총계"""
        return (self.total_liabilities / self.total_equity * 100) if self.total_equity > 0 else 999

    @property
    def retention_ratio(self) -> float:
        """유보율 = 이익잉여금 / 자본금"""
        return (self.retained_earnings / self.capital_stock * 100) if self.capital_stock > 0 else 0


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
        account_nm_clean = account_nm.replace(" ", "").replace("(", "").replace(")", "")

        # 손익계산서 (IS) 또는 포괄손익계산서 (CIS)
        if sj_div in ("IS", "CIS"):
            # 매출액
            if "revenue" in account_id_lower or "매출액" in account_nm or account_nm == "수익(매출액)" or account_nm == "매출":
                m.revenue = max(m.revenue, amount)
            # 매출원가
            elif "costofsales" in account_id_lower or "매출원가" in account_nm:
                m.cost_of_sales = max(m.cost_of_sales, amount)
            # 매출총이익
            elif "grossprofit" in account_id_lower or "매출총이익" in account_nm:
                m.gross_profit = max(m.gross_profit, amount)
            # 영업이익
            elif "operatingincome" in account_id_lower or "영업이익" in account_nm or "영업손익" in account_nm:
                m.operating_income = max(m.operating_income, amount)
            # 금융비용/이자비용
            elif "금융비용" in account_nm or "이자비용" in account_nm or "financecost" in account_id_lower:
                m.finance_cost = max(m.finance_cost, amount)
            # 당기순이익 (더 느슨한 매칭 - 다양한 형태 커버)
            elif "profitloss" in account_id_lower and "comprehensive" not in account_id_lower:
                m.net_income = max(m.net_income, amount)
            elif "netincome" in account_id_lower or "netprofit" in account_id_lower:
                m.net_income = max(m.net_income, amount)
            # 한글 매칭 (더 유연하게)
            elif "당기순이익" in account_nm_clean or "당기순손익" in account_nm_clean:
                m.net_income = max(m.net_income, amount)
            elif "분기순이익" in account_nm_clean or "반기순이익" in account_nm_clean:
                m.net_income = max(m.net_income, amount)
            elif "연결당기순이익" in account_nm_clean or "연결순이익" in account_nm_clean:
                m.net_income = max(m.net_income, amount)
            # "순이익" 또는 "순손익"이 포함되고 "포괄"이 아닌 경우
            elif ("순이익" in account_nm or "순손익" in account_nm) and "포괄" not in account_nm:
                m.net_income = max(m.net_income, amount)
            # 지배기업 귀속 순이익
            elif "지배기업" in account_nm and ("이익" in account_nm or "손익" in account_nm) and "포괄" not in account_nm:
                m.net_income = max(m.net_income, amount)

        # 재무상태표 (BS)
        elif sj_div == "BS":
            # "자본과부채총계" 같은 합계 항목은 무시
            if "자본과부채" in account_nm or "부채와자본" in account_nm:
                continue

            # 자산총계
            if "assets" in account_id_lower and "current" not in account_id_lower and "net" not in account_id_lower:
                m.total_assets = max(m.total_assets, amount)
            elif account_nm == "자산총계" or account_nm == "자산" or account_nm == "자산 계":
                m.total_assets = max(m.total_assets, amount)
            elif "자산총계" in account_nm_clean:
                m.total_assets = max(m.total_assets, amount)
            # 유동자산
            elif "currentassets" in account_id_lower or "유동자산" in account_nm:
                m.current_assets = max(m.current_assets, amount)
            # 현금및현금성자산
            elif "cash" in account_id_lower and "equivalent" in account_id_lower:
                m.cash_and_equivalents = max(m.cash_and_equivalents, amount)
            elif "현금및현금성자산" in account_nm_clean or "현금및현금등가물" in account_nm_clean:
                m.cash_and_equivalents = max(m.cash_and_equivalents, amount)
            elif account_nm_clean in ["현금", "현금및예치금"]:
                m.cash_and_equivalents = max(m.cash_and_equivalents, amount)
            # 부채총계 (정확한 매칭)
            elif "liabilities" in account_id_lower and "current" not in account_id_lower and "asset" not in account_id_lower:
                m.total_liabilities = max(m.total_liabilities, amount)
            elif account_nm == "부채총계" or account_nm == "부채" or account_nm == "부채 계":
                m.total_liabilities = max(m.total_liabilities, amount)
            elif account_nm_clean == "부채총계":
                m.total_liabilities = max(m.total_liabilities, amount)
            # 유동부채
            elif "currentliabilities" in account_id_lower or "유동부채" in account_nm:
                m.current_liabilities = max(m.current_liabilities, amount)
            # 자본총계 (다양한 형태 처리)
            elif "equity" in account_id_lower and "retained" not in account_id_lower and "minority" not in account_id_lower:
                m.total_equity = max(m.total_equity, amount)
            elif account_nm == "자본총계" or account_nm == "자본 총계":
                m.total_equity = max(m.total_equity, amount)
            elif account_nm_clean == "자본총계":
                m.total_equity = max(m.total_equity, amount)
            elif account_nm in ["자본", "자본계", "자본 계"]:
                m.total_equity = max(m.total_equity, amount)
            elif "지배기업" in account_nm and ("지분" in account_nm or "자본" in account_nm):
                m.total_equity = max(m.total_equity, amount)
            elif "지배주주지분" in account_nm or "지배기업소유주지분" in account_nm:
                m.total_equity = max(m.total_equity, amount)
            # 이익잉여금
            elif "retainedearnings" in account_id_lower or "이익잉여금" in account_nm:
                m.retained_earnings = max(m.retained_earnings, amount)
            # 자본금
            elif "issuedcapital" in account_id_lower or "sharecapital" in account_id_lower:
                m.capital_stock = max(m.capital_stock, amount)
            elif account_nm_clean in ["자본금", "보통주자본금", "납입자본"]:
                m.capital_stock = max(m.capital_stock, amount)
            elif "자본금" in account_nm and "잉여금" not in account_nm:
                m.capital_stock = max(m.capital_stock, amount)

        # 현금흐름표 (CF)
        elif sj_div == "CF":
            if "operating" in account_id_lower or "영업활동" in account_nm:
                m.operating_cash_flow = amount
            elif "investing" in account_id_lower or "투자활동" in account_nm:
                m.investing_cash_flow = amount
            elif "financing" in account_id_lower or "재무활동" in account_nm:
                m.financing_cash_flow = amount

    return m


def extract_metrics_with_fallback(statements: list) -> FinancialMetrics:
    """3개년 데이터에서 가장 최근 유효한 값으로 메트릭 추출"""
    # 당기 → 전기 → 전전기 순으로 시도
    current = extract_metrics(statements, "thstrm")
    previous = extract_metrics(statements, "frmtrm")
    before_prev = extract_metrics(statements, "bfefrmtrm")

    # 순이익이 0이면 이전 연도에서 가져오기
    if current.net_income == 0 and previous.net_income != 0:
        current.net_income = previous.net_income
    elif current.net_income == 0 and before_prev.net_income != 0:
        current.net_income = before_prev.net_income

    # 자본총계가 0이면 이전 연도에서 가져오기
    if current.total_equity == 0 and previous.total_equity != 0:
        current.total_equity = previous.total_equity
    elif current.total_equity == 0 and before_prev.total_equity != 0:
        current.total_equity = before_prev.total_equity

    # 자산총계가 0이면 이전 연도에서 가져오기
    if current.total_assets == 0 and previous.total_assets != 0:
        current.total_assets = previous.total_assets

    # 부채총계가 0이면 이전 연도에서 가져오기
    if current.total_liabilities == 0 and previous.total_liabilities != 0:
        current.total_liabilities = previous.total_liabilities

    # 영업이익이 0이면 이전 연도에서 가져오기
    if current.operating_income == 0 and previous.operating_income != 0:
        current.operating_income = previous.operating_income

    return current


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
    # 데이터 출처 정보 (대체 데이터 사용 시)
    data_source: str = ""  # 예: "CFS/2023", "OFS/2022 (연결재무제표 없음)", "OFS/2021 (2년 전 데이터)"


class BuffettAnalyzer:
    """버핏형 가치투자 분석기"""

    async def analyze(self, corp_code: str, corp_name: str, year: str, fs_div: str = "CFS") -> AnalysisResult | None:
        """종합 분석 수행 (데이터 없으면 최대 6년 전까지 fallback, CFS→OFS fallback, 사업보고서→반기보고서 fallback)"""

        statements = None
        actual_year = year
        actual_fs_div = fs_div
        actual_report = "11011"  # 사업보고서
        tried_combinations = []

        # fs_div 우선순위: CFS(연결) → OFS(개별)
        fs_divs_to_try = [fs_div]
        if fs_div == "CFS":
            fs_divs_to_try.append("OFS")  # 연결 없으면 개별로 시도

        # 보고서 유형 우선순위: 11011(사업보고서) → 11012(반기보고서)
        report_codes = ["11011", "11012"]

        # 연도 + 재무제표 유형 + 보고서 유형 조합으로 시도
        for try_fs_div in fs_divs_to_try:
            for year_offset in range(6):  # 0~5년 전 (6년치)
                for reprt_code in report_codes:
                    try_year = str(int(year) - year_offset)
                    data = await dart_client.get_financial_statements(
                        corp_code=corp_code, bsns_year=try_year, reprt_code=reprt_code, fs_div=try_fs_div
                    )

                    status = data.get("status", "unknown")
                    tried_combinations.append(f"{try_fs_div}/{try_year}/{reprt_code}={status}")

                    # 에러 상태 로깅 (999: 네트워크 에러만)
                    if status == "999":
                        print(f"[ANALYZE] {corp_name} {try_fs_div}/{try_year}/{reprt_code}: Network error - {data.get('message', '')[:80]}")

                    if status == "000" and data.get("list"):
                        statements = data.get("list", [])
                        actual_year = try_year
                        actual_fs_div = try_fs_div
                        actual_report = reprt_code
                        break
                if statements:
                    break
            if statements:
                break

        if not statements:
            # 간단한 로그 (상세는 위에서 이미 출력됨)
            print(f"[ANALYZE] {corp_name}: No data (tried {len(tried_combinations)} combinations)")
            return None

        # 데이터 출처 정보 생성
        data_source = f"{actual_fs_div}/{actual_year}"
        year_diff = int(year) - int(actual_year)
        fs_changed = actual_fs_div != fs_div
        report_changed = actual_report != "11011"

        if year_diff > 0 or fs_changed or report_changed:
            notes = []
            if fs_changed:
                notes.append(f"{fs_div} 없음")
            if year_diff > 0:
                notes.append(f"{year_diff}년 전")
            if report_changed:
                notes.append("반기보고서")
            data_source += f" ({', '.join(notes)})"

        # 3개년 지표 추출 (당기 데이터 없으면 전기/전전기에서 fallback)
        current = extract_metrics_with_fallback(statements)
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

        # (5) 현금흐름 질 - 부채비율 (10점)
        cfq_indicator = self._calc_cashflow_quality_buffett(current)
        indicators.append(cfq_indicator)

        # ========================================
        # 보완 지표 (기관급 분석)
        # ========================================

        # (6) ROIC - 투하자본이익률 (15점)
        roic_indicator = self._calc_roic(current)
        indicators.append(roic_indicator)

        # (7) 영업이익률 (10점)
        margin_indicator = self._calc_operating_margin(current)
        indicators.append(margin_indicator)

        # (8) 유보율 (10점)
        retention_indicator = self._calc_retention_ratio(current)
        indicators.append(retention_indicator)

        # (9) 영업이익률 안정성 (10점)
        stability_indicator = self._calc_margin_stability(current, previous, before_prev)
        indicators.append(stability_indicator)

        # 기본 5대 지표만으로 점수 계산 (100점 만점)
        # 보완 지표는 추가 참고용 (+45점)
        # 필터 통과 못하면 0점
        if not filter_result.passed:
            total_score = 0.0
        else:
            # 기본 지표: 처음 5개 (100점 만점)
            base_score = sum(ind.score for ind in indicators[:5])
            # 보완 지표: 6~9번 (45점 만점)
            bonus_score = sum(ind.score for ind in indicators[5:])
            # 총점: 기본 + 보완 가중치 적용 (보완은 30% 반영)
            total_score = base_score + (bonus_score * 0.3)

        # 신호 결정
        signal, recommendation = self._get_signal(total_score, filter_result)

        # fallback 발생 시 recommendation에 표시
        fallback_info = []
        if actual_year != year:
            fallback_info.append(f"{actual_year}년")
        if actual_fs_div != fs_div:
            fs_label = "개별" if actual_fs_div == "OFS" else "연결"
            fallback_info.append(f"{fs_label}재무제표")
        if fallback_info:
            recommendation = f"[{', '.join(fallback_info)} 사용] " + recommendation

        return AnalysisResult(
            corp_code=corp_code,
            corp_name=corp_name,
            year=actual_year,  # 실제 데이터가 있는 연도
            fs_div=actual_fs_div,  # 실제 사용된 재무제표 유형
            indicators=indicators,
            total_score=round(total_score, 1),
            signal=signal,
            recommendation=recommendation,
            filter_result=filter_result,
            metrics={
                "current": current.__dict__,
                "previous": previous.__dict__,
            },
            data_source=data_source
        )

    def _apply_filters(self, current: FinancialMetrics, previous: FinancialMetrics) -> FilterResult:
        """
        2단계: 생존성 및 회계 무결성 검증 (Gemini 하드 필터)

        하나라도 탈락하면 '투자 금지' 대상
        """
        failed_reasons = []

        # === Gemini 필터 1: 현금흐름의 법칙 ===
        # 2년 연속 영업활동현금흐름 < 0 (돈을 못 벌어오는 기업)
        if current.operating_cash_flow < 0 and previous.operating_cash_flow < 0:
            failed_reasons.append("2년 연속 영업현금흐름 마이너스 (현금 창출 실패)")

        # === Gemini 필터 2: 좀비 기업 판독 ===
        # 이자보상배율 < 1.0 (영업이익으로 이자도 못 갚는 기업)
        if current.finance_cost > 0:
            interest_coverage = current.operating_income / current.finance_cost
            if interest_coverage < 1.0:
                failed_reasons.append(f"이자보상배율 {interest_coverage:.1f}배 (이자도 못 갚는 좀비 기업)")

        # === Gemini 필터 3: 자본잠식 체크 ===
        # 자기자본 < 자본금 (회사의 근간이 흔들림)
        if current.total_equity <= 0:
            failed_reasons.append("자본잠식 (자기자본 <= 0)")

        # === 추가 필터: 버핏의 기준 ===
        # 필터 4: 2년 연속 적자 (지속적 손실)
        if current.net_income < 0 and previous.net_income < 0:
            failed_reasons.append("2년 연속 적자")

        # 필터 5: 2년 연속 영업이익 마이너스 (본업에서 돈 못 벌어)
        if current.operating_income < 0 and previous.operating_income < 0:
            failed_reasons.append("2년 연속 영업이익 마이너스 (본업 실패)")

        # 필터 6: 매출액이 없거나 급격히 감소 (사업 중단 위험)
        if current.revenue <= 0:
            failed_reasons.append("매출액 없음")
        elif previous.revenue > 0:
            revenue_change = ((current.revenue - previous.revenue) / previous.revenue) * 100
            if revenue_change < -50:
                failed_reasons.append(f"매출액 급감 ({revenue_change:.1f}% - 사업 축소)")

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

    # ============================================
    # 보완 지표 (Gemini 추천)
    # ============================================

    def _calc_roic(self, m: FinancialMetrics) -> Indicator:
        """
        ROIC (투하자본이익률) - 15점 만점
        기관 기준: 15% 이상 우수
        """
        max_score = 15
        roic = m.roic  # property 사용

        if roic >= 20:
            score = 15  # 탁월
        elif roic >= 15:
            score = 12  # 우수
        elif roic >= 10:
            score = 8   # 양호
        elif roic >= 5:
            score = 4   # 보통
        else:
            score = 0   # 미흡

        grade = self._score_to_grade(score, max_score)

        return Indicator(
            name="ROIC (투하자본이익률)",
            value=round(roic, 1),
            score=score,
            max_score=max_score,
            grade=grade,
            description=f"투하자본 대비 {roic:.1f}% 수익" if roic > 0 else "수익 미흡",
            good_criteria="15% 이상 (순수 영업 실력)",
            category="수익성"
        )

    def _calc_operating_margin(self, m: FinancialMetrics) -> Indicator:
        """
        영업이익률 - 10점 만점
        가격 결정력(해자) 지표
        """
        max_score = 10
        margin = m.operating_margin  # property 사용

        if margin >= 20:
            score = 10  # 탁월한 해자
        elif margin >= 15:
            score = 8   # 우수
        elif margin >= 10:
            score = 6   # 양호
        elif margin >= 5:
            score = 3   # 보통
        else:
            score = 0   # 미흡

        grade = self._score_to_grade(score, max_score)

        return Indicator(
            name="영업이익률",
            value=round(margin, 1),
            score=score,
            max_score=max_score,
            grade=grade,
            description=f"매출 대비 {margin:.1f}% 영업이익" if margin > 0 else "영업이익 없음",
            good_criteria="15% 이상 (가격 결정력 보유)",
            category="수익성"
        )

    def _calc_retention_ratio(self, m: FinancialMetrics) -> Indicator:
        """
        유보율 - 10점 만점
        위기 대응 능력 지표
        """
        max_score = 10
        ratio = m.retention_ratio  # property 사용

        if ratio >= 1000:
            score = 10  # 매우 우수
        elif ratio >= 500:
            score = 8   # 우수 (기관 기준)
        elif ratio >= 300:
            score = 5   # 양호
        elif ratio >= 100:
            score = 2   # 보통
        else:
            score = 0   # 미흡

        grade = self._score_to_grade(score, max_score)

        return Indicator(
            name="유보율",
            value=round(ratio, 1),
            score=score,
            max_score=max_score,
            grade=grade,
            description=f"자본금 대비 {ratio:.0f}% 유보" if ratio > 0 else "유보금 없음",
            good_criteria="500% 이상 (위기 대응력 우수)",
            category="안정성"
        )

    def _calc_margin_stability(self, curr: FinancialMetrics, prev: FinancialMetrics, bprev: FinancialMetrics) -> Indicator:
        """
        영업이익률 안정성 - 10점 만점
        3년간 영업이익률 변동성 (해자 지속성)
        """
        max_score = 10

        margins = []
        if curr.revenue > 0:
            margins.append(curr.operating_margin)
        if prev.revenue > 0:
            margins.append(prev.operating_margin)
        if bprev.revenue > 0:
            margins.append(bprev.operating_margin)

        if len(margins) < 2:
            return Indicator("영업이익률 안정성", 0, 5, max_score, "C",
                           "데이터 부족", "3년 연속 10% 이상 유지", "해자")

        avg_margin = sum(margins) / len(margins)
        # 표준편차 계산
        variance = sum((m - avg_margin) ** 2 for m in margins) / len(margins)
        std_dev = variance ** 0.5

        # 평균 마진이 10% 이상이고 변동성이 낮으면 해자 보유
        if avg_margin >= 10 and std_dev < 3:
            score = 10  # 안정적 해자
        elif avg_margin >= 10 and std_dev < 5:
            score = 8   # 해자 보유
        elif avg_margin >= 7 and std_dev < 5:
            score = 5   # 양호
        elif avg_margin >= 5:
            score = 3   # 보통
        else:
            score = 0   # 해자 없음

        grade = self._score_to_grade(score, max_score)

        return Indicator(
            name="영업이익률 안정성",
            value=round(avg_margin, 1),
            score=score,
            max_score=max_score,
            grade=grade,
            description=f"3년 평균 {avg_margin:.1f}% (변동성 {std_dev:.1f}%p)",
            good_criteria="3년 연속 10% 이상 + 낮은 변동성",
            category="해자"
        )

    def _score_to_grade(self, score: float, max_score: float) -> str:
        """점수를 등급으로 변환 (S~F with +++/++/+/-/--/---, 총 49단계)"""
        ratio = score / max_score if max_score > 0 else 0

        # S~F 등급 (7개), 각 등급당 +++, ++, +, 기본, -, --, --- (7단계씩 = 49단계)
        grades = ['S', 'A', 'B', 'C', 'D', 'E', 'F']
        modifiers = ['+++', '++', '+', '', '-', '--', '---']

        # 비율을 49등급으로 변환 (0~48)
        grade_index = int((1 - ratio) * 49)
        grade_index = min(48, max(0, grade_index))  # 0~48 범위 제한

        letter_index = grade_index // 7  # 0~6 (S~F)
        modifier_index = grade_index % 7  # 0~6 (+++, ++, +, 기본, -, --, ---)

        return f"{grades[letter_index]}{modifiers[modifier_index]}"

    def _get_signal(self, total_score: float, filter_result: FilterResult) -> tuple[str, str]:
        """매매 신호 결정 (10단계 세분화)"""
        if not filter_result.passed:
            reasons = ", ".join(filter_result.failed_reasons[:2])
            return "투자부적격", f"필터링 탈락: {reasons}"

        # 10단계 세분화된 신호
        if total_score >= 90:
            return "S급 강력매수", "최상위권 종목. 버핏이 사랑할 기업. 장기 보유 강력 추천."
        elif total_score >= 80:
            return "A급 강력매수", "모든 지표가 버핏 기준 충족. 장기 투자 적합."
        elif total_score >= 72:
            return "A급 매수", "대부분의 지표가 우수. 적극적 투자 검토 권장."
        elif total_score >= 65:
            return "B급 매수", "주요 지표 양호. 투자 검토 권장."
        elif total_score >= 58:
            return "B급 관망(매수우위)", "괜찮은 편. 추가 분석 후 투자 고려."
        elif total_score >= 50:
            return "C급 관망", "일부 지표 부족. 신중한 검토 필요."
        elif total_score >= 42:
            return "C급 관망(매도우위)", "부정적 지표 다수. 투자 주의."
        elif total_score >= 35:
            return "D급 매도", "여러 지표 부정적. 보유 시 손절 검토."
        elif total_score >= 25:
            return "D급 강력매도", "대부분 지표 미달. 투자 회피."
        else:
            return "F급 회피", "심각한 재무 상태. 절대 투자 금지."


# 싱글톤
financial_analyzer = BuffettAnalyzer()
