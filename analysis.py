from models import AnalysisResult, FinancialIndicator
from services import DartService

class StockAnalyzer:
    def __init__(self):
        self.service = DartService()

    def _get_account_value(self, data_list, account_id):
        """재무제표 리스트에서 특정 계정 값을 찾아 반환"""
        if not data_list: return 0
        for item in data_list:
            # PDF 예시 데이터의 account_id 매핑 [cite: 585, 821, 923]
            if item.get("account_id") == account_id:
                amount = item.get("thstrm_amount", "0").replace(",", "")
                return float(amount) if amount else 0
        return 0

    async def analyze(self, corp_code: str, corp_name: str) -> AnalysisResult:
        # 1. 데이터 수집
        fs_data = await self.service.get_financial_statement(corp_code)
        cb_data = await self.service.get_cb_issuance(corp_code)
        insider_data = await self.service.get_insider_trading(corp_code)
        
        fs_list = fs_data.get("list", [])
        
        indicators = []
        score = 0

        # --- 1. 현금 창출 능력 (Cash Flow) [cite: 531-537] ---
        # 영업활동현금흐름 > 당기순이익
        op_cash_flow = self._get_account_value(fs_list, "ifrs_CashFlowsFromUsedInOperatingActivities")
        net_income = self._get_account_value(fs_list, "ifrs_ProfitLoss")
        
        cf_status = "danger"
        if op_cash_flow > net_income and op_cash_flow > 0:
            cf_status = "success"
            score += 20
        
        indicators.append(FinancialIndicator(
            name="현금 창출 능력 (PCR 대용)",
            value=f"OCF: {op_cash_flow:,.0f} / NI: {net_income:,.0f}",
            status=cf_status,
            description="영업활동현금흐름이 당기순이익보다 커야 합니다. (흑자도산 방지)",
            threshold="OCF > Net Income"
        ))

        # --- 2. 재무 안정성 (Financial Stability) [cite: 538-546] ---
        # 이자보상배율 = 영업이익 / 이자비용
        op_income = self._get_account_value(fs_list, "dart_OperatingIncomeLoss")
        # PDF 예시에서 이자비용은 '-표준계정코드 미사용-' 또는 'finance_cost' 등으로 나올 수 있음
        # 여기서는 PDF [cite: 541]에 따라 금융비용 근사치 사용 (예시 로직)
        interest_expense = abs(self._get_account_value(fs_list, "ifrs_FinanceCosts")) # 없으면 0
        if interest_expense == 0: interest_expense = 1 # Div zero 방지

        icr = op_income / interest_expense
        icr_status = "danger"
        if icr >= 3.0: # [cite: 544]
            icr_status = "success"
            score += 20
        elif icr >= 1.5: # [cite: 545]
            icr_status = "warning"
            score += 10
            
        indicators.append(FinancialIndicator(
            name="재무 안정성 (이자보상배율)",
            value=f"{icr:.2f}배",
            status=icr_status,
            description="영업이익으로 이자비용을 감당할 수 있는 능력입니다.",
            threshold="> 3.0 (Good), > 1.5 (Normal)"
        ))

        # --- 3. 성장성 (Growth) [cite: 548-555] ---
        # 영업이익 성장률 (YoY)
        # API는 당기(thstrm), 전기(frmtrm) 데이터를 함께 줌 [cite: 821-822]
        prev_op_income = 0
        for item in fs_list:
            if item.get("account_id") == "dart_OperatingIncomeLoss":
                prev_amount = item.get("frmtrm_amount", "0").replace(",", "")
                prev_op_income = float(prev_amount) if prev_amount else 0
                break
        
        growth_rate = 0
        if prev_op_income != 0:
            growth_rate = ((op_income - prev_op_income) / abs(prev_op_income)) * 100
            
        growth_status = "danger"
        if growth_rate >= 15: # [cite: 553]
            growth_status = "success"
            score += 20
        elif growth_rate >= 0: # [cite: 554]
            growth_status = "warning"
            score += 10

        indicators.append(FinancialIndicator(
            name="성장성 (영업이익 성장률)",
            value=f"{growth_rate:.2f}%",
            status=growth_status,
            description="전년 대비 영업이익이 얼마나 증가했는지 확인합니다.",
            threshold="> 15% (High Growth)"
        ))

        # --- 4. 수급 및 리스크 (Overhang) [cite: 556-565] ---
        # (미상환 전환사채 / 총 주식수) 비율
        # 예시 구현을 위해 CB 총액과 자본금 대비 비율로 간소화 (정확한 주식수는 별도 API 필요하나 PDF 내용 기반 추정)
        total_cb_amount = 0
        if cb_data.get("list"):
            for cb in cb_data["list"]:
                # [cite: 1014] bd_fta (사채권면총액) 사용
                total_cb_amount += float(cb.get("bd_fta", "0").replace(",", ""))
        
        equity = self._get_account_value(fs_list, "ifrs_TotalEquity") # 자본총계 대용
        if equity == 0: equity = 1
        
        dilution_ratio = (total_cb_amount / equity) * 100 # 자본 대비 희석 가능성으로 근사
        
        risk_status = "success"
        if dilution_ratio == 0: # [cite: 563]
            score += 20
        elif dilution_ratio < 5: # [cite: 564]
            risk_status = "warning"
            score += 15
        elif dilution_ratio >= 10: # [cite: 565]
            risk_status = "danger"
            score += 0

        indicators.append(FinancialIndicator(
            name="잠재 리스크 (희석 가능 물량)",
            value=f"자본 대비 CB 비율: {dilution_ratio:.2f}%",
            status=risk_status,
            description="전환사채(CB) 등 향후 주식으로 전환되어 매물화될 수 있는 물량입니다.",
            threshold="< 5% (Safe), 0% (Best)"
        ))

        # --- 5. 내부자 확신 (Insider) [cite: 566-572] ---
        # 최근 3~6개월 임원/주요주주 순매수
        insider_buy_count = 0
        insider_sell_count = 0
        net_quantity = 0
        
        if insider_data.get("list"):
            # 최근 3개월 필터링 로직 필요 (여기선 전체 합산 예시)
            for trade in insider_data["list"]:
                qty = float(trade.get("sp_stock_lmp_cnt", "0").replace(",", "")) # 
                if qty > 0: insider_buy_count += 1
                elif qty < 0: insider_sell_count += 1
                net_quantity += qty

        insider_status = "warning"
        if net_quantity > 0 and insider_buy_count >= 2: # [cite: 571]
            insider_status = "success"
            score += 20
        elif net_quantity < 0: # [cite: 572]
            insider_status = "danger"
            
        indicators.append(FinancialIndicator(
            name="내부자 확신 (임원 매매)",
            value=f"순매수량: {net_quantity:,.0f}주",
            status=insider_status,
            description="회사를 가장 잘 아는 임원 및 대주주의 장내 매수 여부입니다.",
            threshold="3개월 내 2인 이상 매수 (Positive)"
        ))

        # 종합 등급 산정
        grade = "F"
        if score >= 80: grade = "S"
        elif score >= 60: grade = "A"
        elif score >= 40: grade = "B"
        elif score >= 20: grade = "C"

        return AnalysisResult(
            corp_name=corp_name,
            corp_code=corp_code,
            score=score,
            grade=grade,
            indicators=indicators,
            total_comment=f"종합 점수 {score}점으로 투자 매력도는 '{grade}' 등급입니다."
        )