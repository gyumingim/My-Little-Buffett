"""
Stage 2: Value Score - 펀더멘탈 점수 계산
"""
from pathlib import Path
from typing import Dict
from .utils import get_safe_value, get_financial_data, load_json_safe


class ValueScorer:
    """펀더멘탈 점수 계산 (0~100점)"""

    def __init__(self, data_path: Path):
        self.data_path = data_path

    def score_cash_generation(self, corp_code: str) -> Dict[str, any]:
        """
        현금 창출력 점수 (30점 만점)

        공식: 영업활동현금흐름 / 시가총액 (또는 자산총계)
        """
        data, source = get_financial_data(corp_code, self.data_path, "2024")

        if not data or not data.get('list'):
            return {"score": 0, "reason": "데이터 없음"}

        financial_items = {item['account_id']: item for item in data['list']}

        # 영업활동현금흐름
        operating_cf = get_safe_value(
            financial_items.get('ifrs-full_CashFlowsFromUsedInOperatingActivities', {}),
            'thstrm_amount',
            0
        )

        # 자산총계 (시가총액 대체)
        assets = get_safe_value(
            financial_items.get('ifrs-full_Assets', {}),
            'thstrm_amount',
            1
        )

        if assets <= 0 or operating_cf <= 0:
            return {"score": 0, "reason": "현금흐름 부족", "ratio": 0}

        cf_ratio = operating_cf / assets

        # 점수 계산
        if cf_ratio >= 0.15:  # 15% 이상
            score = 30
        elif cf_ratio >= 0.10:  # 10% 이상
            score = 20
        elif cf_ratio >= 0.05:  # 5% 이상
            score = 10
        else:
            score = 0

        return {
            "score": score,
            "reason": f"영업CF/자산: {cf_ratio*100:.2f}%",
            "ratio": cf_ratio
        }

    def score_subsidiary_health(self, corp_code: str) -> Dict[str, any]:
        """
        자회사 건전성 점수 (20점 만점)

        공식: CFS 당기순이익 - OFS 당기순이익
        """
        cfs_data, _ = get_financial_data(corp_code, self.data_path, "2024")

        # OFS 데이터 직접 로드
        ofs_path = self.data_path / "OFS" / "2024" / f"{corp_code}.json"
        ofs_data = load_json_safe(ofs_path)

        if not cfs_data or not cfs_data.get('list'):
            return {"score": 10, "reason": "CFS 데이터 없음 (중립)"}

        if not ofs_data or not ofs_data.get('list'):
            # 연결만 있는 경우 (자회사 없거나 외국계)
            cfs_items = {item['account_id']: item for item in cfs_data['list']}
            cfs_profit = get_safe_value(
                cfs_items.get('ifrs-full_ProfitLoss', {}),
                'thstrm_amount',
                0
            )

            if cfs_profit > 0:
                return {"score": 15, "reason": "연결재무제표만 존재 (자회사 없음, 흑자)", "diff": 0}
            else:
                return {"score": 0, "reason": "연결재무제표만 존재 (적자)", "diff": 0}

        # CFS와 OFS 모두 있는 경우
        cfs_items = {item['account_id']: item for item in cfs_data['list']}
        ofs_items = {item['account_id']: item for item in ofs_data['list']}

        cfs_profit = get_safe_value(
            cfs_items.get('ifrs-full_ProfitLoss', {}),
            'thstrm_amount',
            0
        )

        ofs_profit = get_safe_value(
            ofs_items.get('ifrs-full_ProfitLoss', {}),
            'thstrm_amount',
            0
        )

        diff = cfs_profit - ofs_profit

        # 점수 계산
        if diff > 0:
            # 자회사가 돈을 벌어오고 있음
            score = 20
            reason = f"자회사 기여도 양호 (차이: {diff:,.0f})"
        elif ofs_profit > 0 and abs(diff) / ofs_profit > 0.3:
            # 자회사 적자가 심각
            score = 0
            reason = f"자회사 적자 심각 (차이: {diff:,.0f})"
        else:
            # 중립
            score = 10
            reason = f"자회사 영향 미미 (차이: {diff:,.0f})"

        return {"score": score, "reason": reason, "diff": diff}

    def score_expansion(self, corp_code: str) -> Dict[str, any]:
        """
        사업 확장성 점수 (20점 만점)

        활용: INV (타법인 출자)
        """
        inv_path = self.data_path / "INV" / "2024" / f"{corp_code}.json"
        inv_data = load_json_safe(inv_path)

        if not inv_data or not inv_data.get('list'):
            return {"score": 10, "reason": "타법인 출자 정보 없음 (중립)"}

        # 흑자 자회사 vs 적자 자회사 카운트
        profitable_count = 0
        loss_count = 0

        for item in inv_data['list']:
            # 최근 사업연도 당기순손익
            profit_str = item.get('recent_bsns_year_ntpf', '0')
            profit = get_safe_value({"val": profit_str}, "val", 0)

            if profit > 0:
                profitable_count += 1
            elif profit < 0:
                loss_count += 1

        # 점수 계산
        if profitable_count > loss_count and profitable_count > 0:
            score = 20
            reason = f"알짜 자회사 보유 (흑자 {profitable_count}개, 적자 {loss_count}개)"
        elif loss_count > profitable_count:
            score = 5
            reason = f"적자 자회사 증가 (흑자 {profitable_count}개, 적자 {loss_count}개)"
        else:
            score = 10
            reason = "타법인 출자 정보 부족"

        return {"score": score, "reason": reason}

    def score_shareholder_return(self, corp_code: str) -> Dict[str, any]:
        """
        주주 환원 의지 점수 (30점 만점)

        활용: ACQ (자사주 취득/소각)
        """
        acq_path = self.data_path / "ACQ" / "2024" / f"{corp_code}.json"
        acq_data = load_json_safe(acq_path)

        if not acq_data or not acq_data.get('list'):
            return {"score": 0, "reason": "자사주 취득 없음"}

        # 최근 1년 내 자사주 취득 여부
        has_acquisition = len(acq_data['list']) > 0

        if has_acquisition:
            # 소각 여부 확인 (공시 내용에서 "소각" 키워드 검색)
            purpose = acq_data['list'][0].get('aq_pp', '')

            if '소각' in purpose or 'cancellation' in purpose.lower():
                score = 30
                reason = "자사주 취득 + 소각 예정"
            else:
                score = 15
                reason = "자사주 취득 (소각 미정)"
        else:
            score = 0
            reason = "자사주 취득 없음"

        return {"score": score, "reason": reason}

    def calculate_total_score(self, corp_code: str) -> Dict[str, any]:
        """
        총 점수 계산 (0~100점)

        Returns:
            {
                "total_score": int,
                "breakdown": {
                    "cash": {...},
                    "subsidiary": {...},
                    "expansion": {...},
                    "shareholder": {...}
                }
            }
        """
        breakdown = {
            "cash": self.score_cash_generation(corp_code),
            "subsidiary": self.score_subsidiary_health(corp_code),
            "expansion": self.score_expansion(corp_code),
            "shareholder": self.score_shareholder_return(corp_code)
        }

        total_score = sum(item["score"] for item in breakdown.values())

        return {
            "total_score": total_score,
            "breakdown": breakdown
        }
