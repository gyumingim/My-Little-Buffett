"""
Stage 3: Catalyst Boost - 가산점 부여
"""
from pathlib import Path
from typing import Dict
from .utils import load_json_safe


class CatalystBooster:
    """가산점(Boost) 계산"""

    def __init__(self, data_path: Path):
        self.data_path = data_path

    def boost_insider_buying(self, corp_code: str) -> Dict[str, any]:
        """
        임원 매수 부스터 (+10점)

        활용: EXEC
        """
        exec_path = self.data_path / "EXEC" / "2024" / f"{corp_code}.json"
        exec_data = load_json_safe(exec_path)

        if not exec_data or not exec_data.get('list'):
            return {"boost": 0, "reason": "임원 매수 정보 없음"}

        # 최근 공시 확인
        for item in exec_data['list']:
            # 보고사유가 '장내매수' 등인지 확인
            report_reason = item.get('isu_exctv_ofcps', '')

            # 대표이사 또는 등기임원
            if '대표이사' in report_reason or '등기임원' in report_reason:
                # 주식 수 증가 여부 확인
                increase_count = item.get('sp_stock_lmp_irds_cnt', '0')
                if increase_count != '0' and increase_count != '-':
                    return {
                        "boost": 10,
                        "reason": f"임원 장내 매수 감지 ({report_reason})"
                    }

        return {"boost": 0, "reason": "유의미한 임원 매수 없음"}

    def boost_facility_investment(self, corp_code: str) -> Dict[str, any]:
        """
        시설 투자 부스터 (+10점)

        활용: DEC (증자 목적)
        """
        dec_path = self.data_path / "DEC" / "2024" / f"{corp_code}.json"
        dec_data = load_json_safe(dec_path)

        if not dec_data or not dec_data.get('list'):
            return {"boost": 0, "reason": "증자 정보 없음"}

        for item in dec_data['list']:
            # 자금 사용 목적 확인
            facility_purpose = item.get('fdpp_fclt', '-')
            business_purpose = item.get('fdpp_bsninh', '-')

            if facility_purpose != '-' or business_purpose != '-':
                return {
                    "boost": 10,
                    "reason": "시설투자 또는 사업확장 목적 증자"
                }

        return {"boost": 0, "reason": "성장성 증자 없음"}

    def boost_smart_money(self, corp_code: str) -> Dict[str, any]:
        """
        큰손 입성 부스터 (+5점)

        활용: DEC, CB (투자자 정보)
        """
        dec_path = self.data_path / "DEC" / "2024" / f"{corp_code}.json"
        dec_data = load_json_safe(dec_path)

        if not dec_data or not dec_data.get('list'):
            return {"boost": 0, "reason": "투자자 정보 없음"}

        # 제3자 배정 여부 확인
        for item in dec_data['list']:
            method = item.get('ic_mthn', '')

            if '제3자배정' in method:
                return {
                    "boost": 5,
                    "reason": "제3자 배정 증자 (스마트머니 가능성)"
                }

        return {"boost": 0, "reason": "일반 증자"}

    def calculate_total_boost(self, corp_code: str) -> Dict[str, any]:
        """
        총 부스터 점수 계산

        Returns:
            {
                "total_boost": int,
                "boosters": {
                    "insider": {...},
                    "facility": {...},
                    "smart_money": {...}
                }
            }
        """
        boosters = {
            "insider": self.boost_insider_buying(corp_code),
            "facility": self.boost_facility_investment(corp_code),
            "smart_money": self.boost_smart_money(corp_code)
        }

        total_boost = sum(item["boost"] for item in boosters.values())

        return {
            "total_boost": total_boost,
            "boosters": boosters
        }
