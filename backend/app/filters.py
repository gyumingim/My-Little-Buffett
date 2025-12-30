"""
Stage 1: Death Filter - 위험 기업 필터링
"""
from pathlib import Path
from typing import Dict, List, Optional
from .utils import get_safe_value, get_financial_data, load_json_safe, parse_amount


class DeathFilter:
    """위험 기업을 걸러내는 필터"""

    def __init__(self, data_path: Path):
        self.data_path = data_path

    def check_zombie_company(self, corp_code: str) -> Dict[str, any]:
        """
        좀비 기업 체크: 영업이익 < 금융비용 (이자보상배율 1 미만) 2년 연속

        Returns:
            {"passed": bool, "reason": str, "data": dict}
        """
        years = ["2024", "2023"]
        low_icr_count = 0

        for year in years:
            data, source = get_financial_data(corp_code, self.data_path, year)

            if not data or not data.get('list'):
                continue

            # CIS (포괄손익계산서)에서 영업이익과 금융비용 추출
            financial_items = {item['account_id']: item for item in data['list']}

            operating_profit = get_safe_value(
                financial_items.get('dart_OperatingIncomeLoss', {}),
                'thstrm_amount',
                0
            )

            finance_cost = get_safe_value(
                financial_items.get('ifrs-full_FinanceCosts', {}),
                'thstrm_amount',
                0
            )

            # 이자보상배율 계산
            if finance_cost > 0:
                icr = operating_profit / finance_cost
                if icr < 1.0:
                    low_icr_count += 1

        if low_icr_count >= 2:
            return {
                "passed": False,
                "reason": "좀비 기업 (이자보상배율 1 미만, 2년 연속)",
                "severity": "CRITICAL"
            }

        return {"passed": True, "reason": "정상", "severity": "SAFE"}

    def check_fake_profit(self, corp_code: str) -> Dict[str, any]:
        """
        가짜 이익 체크: 당기순이익은 흑자인데 영업활동현금흐름이 적자

        Returns:
            {"passed": bool, "reason": str}
        """
        data, source = get_financial_data(corp_code, self.data_path, "2024")

        if not data or not data.get('list'):
            return {"passed": True, "reason": "데이터 없음", "severity": "UNKNOWN"}

        financial_items = {item['account_id']: item for item in data['list']}

        # 당기순이익
        profit = get_safe_value(
            financial_items.get('ifrs-full_ProfitLoss', {}),
            'thstrm_amount',
            0
        )

        # 영업활동현금흐름
        operating_cf = get_safe_value(
            financial_items.get('ifrs-full_CashFlowsFromUsedInOperatingActivities', {}),
            'thstrm_amount',
            0
        )

        if profit > 0 and operating_cf < 0:
            return {
                "passed": False,
                "reason": f"가짜 이익 (순이익 {profit:,.0f}, 영업CF {operating_cf:,.0f})",
                "severity": "HIGH"
            }

        return {"passed": True, "reason": "정상", "severity": "SAFE"}

    def check_fund_misuse(self, corp_code: str) -> Dict[str, any]:
        """
        주주 뒤통수 체크: 자금 사용 목적 외 사용

        Returns:
            {"passed": bool, "reason": str}
        """
        use_path = self.data_path / "USE" / "2024" / f"{corp_code}.json"
        use_data = load_json_safe(use_path)

        if not use_data or not use_data.get('list'):
            return {"passed": True, "reason": "자금사용 공시 없음", "severity": "SAFE"}

        for item in use_data['list']:
            diff_reason = item.get('dffrnc_occrrnc_resn', '-')
            if diff_reason and diff_reason != '-':
                return {
                    "passed": False,
                    "reason": f"목적 외 사용: {diff_reason}",
                    "severity": "HIGH"
                }

        return {"passed": True, "reason": "정상", "severity": "SAFE"}

    def check_litigation_risk(self, corp_code: str) -> Dict[str, any]:
        """
        소송 리스크 체크: 청구금액 > 자기자본의 10%

        Returns:
            {"passed": bool, "reason": str}
        """
        lit_path = self.data_path / "LIT" / "2024" / f"{corp_code}.json"
        lit_data = load_json_safe(lit_path)

        if not lit_data or not lit_data.get('list'):
            return {"passed": True, "reason": "소송 없음", "severity": "SAFE"}

        # 자기자본 조회
        data, source = get_financial_data(corp_code, self.data_path, "2024")
        if not data:
            return {"passed": True, "reason": "재무데이터 없음", "severity": "UNKNOWN"}

        financial_items = {item['account_id']: item for item in data['list']}
        equity = get_safe_value(
            financial_items.get('ifrs-full_Equity', {}),
            'thstrm_amount',
            1  # 0으로 나누기 방지
        )

        # 소송 금액 합계
        total_claim = 0
        for item in lit_data['list']:
            claim_amt = parse_amount(item.get('claim_amt', '0'))
            total_claim += claim_amt

        if equity > 0:
            risk_ratio = total_claim / equity

            if risk_ratio > 0.1:  # 10% 초과
                return {
                    "passed": False,
                    "reason": f"소송 리스크 (청구금액 {total_claim:,.0f}, 자기자본 대비 {risk_ratio*100:.1f}%)",
                    "severity": "HIGH"
                }

        return {"passed": True, "reason": "정상", "severity": "SAFE"}

    def check_dilution_bomb(self, corp_code: str) -> Dict[str, any]:
        """
        물량 폭탄 체크: 미상환 사채 주식수 > 총 주식수의 20%

        Returns:
            {"passed": bool, "reason": str}
        """
        cb_path = self.data_path / "CB" / "2024" / f"{corp_code}.json"
        cb_data = load_json_safe(cb_path)

        if not cb_data or not cb_data.get('list'):
            return {"passed": True, "reason": "전환사채 없음", "severity": "SAFE"}

        # 총 주식수 조회 (재무상태표에서)
        data, source = get_financial_data(corp_code, self.data_path, "2024")
        if not data:
            return {"passed": True, "reason": "재무데이터 없음", "severity": "UNKNOWN"}

        # 자본금에서 주식수 추산 (자본금 / 액면가)
        financial_items = {item['account_id']: item for item in data['list']}
        capital = get_safe_value(
            financial_items.get('ifrs-full_IssuedCapital', {}),
            'thstrm_amount',
            0
        )

        # 일반적으로 액면가 500원 가정
        total_shares = capital / 500 if capital > 0 else 1

        # CB 주식수 합계
        total_cb_shares = 0
        for item in cb_data['list']:
            cb_shares_str = item.get('ovis_ster', '0')
            if cb_shares_str and cb_shares_str != '-':
                try:
                    cb_shares = float(cb_shares_str.replace(',', ''))
                    total_cb_shares += cb_shares
                except:
                    pass

        dilution_ratio = total_cb_shares / total_shares if total_shares > 0 else 0

        if dilution_ratio > 0.2:  # 20% 초과
            return {
                "passed": False,
                "reason": f"물량 폭탄 (CB 주식수 {total_cb_shares:,.0f}, 희석률 {dilution_ratio*100:.1f}%)",
                "severity": "HIGH"
            }

        return {"passed": True, "reason": "정상", "severity": "SAFE"}

    def run_all_filters(self, corp_code: str) -> Dict[str, any]:
        """
        모든 필터 실행

        Returns:
            {
                "passed": bool,
                "filters": {
                    "zombie": {...},
                    "fake_profit": {...},
                    ...
                },
                "severity": "SAFE" | "UNKNOWN" | "HIGH" | "CRITICAL"
            }
        """
        results = {
            "zombie": self.check_zombie_company(corp_code),
            "fake_profit": self.check_fake_profit(corp_code),
            "fund_misuse": self.check_fund_misuse(corp_code),
            "litigation": self.check_litigation_risk(corp_code),
            "dilution": self.check_dilution_bomb(corp_code)
        }

        # 하나라도 통과 못하면 탈락
        all_passed = all(r["passed"] for r in results.values())

        # 가장 높은 심각도 추출
        severities = [r["severity"] for r in results.values()]
        severity_order = ["CRITICAL", "HIGH", "UNKNOWN", "SAFE"]
        max_severity = next((s for s in severity_order if s in severities), "SAFE")

        return {
            "passed": all_passed,
            "filters": results,
            "severity": max_severity
        }
