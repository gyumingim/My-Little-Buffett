"""
Main Alpha Finder Engine - 통합 분석 엔진
"""
from pathlib import Path
from typing import Dict, List
from .filters import DeathFilter
from .scoring import ValueScorer
from .boosters import CatalystBooster


class AlphaFinder:
    """My Little Buffett - Alpha Finder 메인 엔진"""

    def __init__(self, data_path: Path):
        self.data_path = Path(data_path)
        self.death_filter = DeathFilter(self.data_path)
        self.value_scorer = ValueScorer(self.data_path)
        self.catalyst_booster = CatalystBooster(self.data_path)

    def analyze_company(self, corp_code: str) -> Dict[str, any]:
        """
        단일 기업 분석

        Returns:
            {
                "corp_code": str,
                "stage1_filter": {...},
                "stage2_score": {...},
                "stage3_boost": {...},
                "final_score": int,
                "grade": str,
                "recommendation": str
            }
        """
        # Stage 1: Death Filter
        filter_result = self.death_filter.run_all_filters(corp_code)

        # 필터 통과 못하면 F등급
        if not filter_result["passed"]:
            return {
                "corp_code": corp_code,
                "stage1_filter": filter_result,
                "stage2_score": None,
                "stage3_boost": None,
                "final_score": 0,
                "grade": "F",
                "recommendation": "투자 부적합 (위험 기업)"
            }

        # Stage 2: Value Score
        score_result = self.value_scorer.calculate_total_score(corp_code)

        # Stage 3: Catalyst Boost
        boost_result = self.catalyst_booster.calculate_total_boost(corp_code)

        # Final Score
        final_score = score_result["total_score"] + boost_result["total_boost"]

        # Grade
        grade = self._calculate_grade(final_score)

        # Recommendation
        recommendation = self._generate_recommendation(grade, filter_result, score_result, boost_result)

        return {
            "corp_code": corp_code,
            "stage1_filter": filter_result,
            "stage2_score": score_result,
            "stage3_boost": boost_result,
            "final_score": final_score,
            "grade": grade,
            "recommendation": recommendation
        }

    def analyze_batch(self, corp_codes: List[str]) -> List[Dict[str, any]]:
        """
        여러 기업 분석

        Args:
            corp_codes: 기업 코드 리스트

        Returns:
            분석 결과 리스트 (final_score 내림차순 정렬)
        """
        results = []

        for corp_code in corp_codes:
            try:
                result = self.analyze_company(corp_code)
                results.append(result)
            except Exception as e:
                print(f"Error analyzing {corp_code}: {e}")
                results.append({
                    "corp_code": corp_code,
                    "error": str(e),
                    "final_score": 0,
                    "grade": "ERROR"
                })

        # 점수순 정렬
        results.sort(key=lambda x: x.get("final_score", 0), reverse=True)

        return results

    def _calculate_grade(self, score: int) -> str:
        """점수에 따른 등급 계산"""
        if score >= 90:
            return "S"
        elif score >= 80:
            return "A+"
        elif score >= 70:
            return "A"
        elif score >= 60:
            return "B+"
        elif score >= 50:
            return "B"
        elif score >= 40:
            return "C"
        else:
            return "D"

    def _generate_recommendation(
        self,
        grade: str,
        filter_result: Dict,
        score_result: Dict,
        boost_result: Dict
    ) -> str:
        """추천 메시지 생성"""
        if grade in ["S", "A+", "A"]:
            catalysts = []
            for key, value in boost_result["boosters"].items():
                if value["boost"] > 0:
                    catalysts.append(value["reason"])

            if catalysts:
                return f"강력 매수 추천. 촉매: {', '.join(catalysts)}"
            else:
                return "매수 추천 (펀더멘탈 우량)"

        elif grade in ["B+", "B"]:
            return "관심 종목 (모니터링 필요)"

        elif grade == "C":
            return "보통 (신중한 접근 필요)"

        else:
            return "투자 비추천"
