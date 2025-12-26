from pydantic import BaseModel
from enum import Enum


class SignalType(str, Enum):
    """투자 신호 유형"""

    STRONG_BUY = "strong_buy"
    BUY = "buy"
    HOLD = "hold"
    SELL = "sell"
    STRONG_SELL = "strong_sell"
    CAUTION = "caution"


class IndicatorBase(BaseModel):
    """지표 기본 스키마"""

    name: str
    description: str
    signal: SignalType
    signal_description: str


class CashGenerationIndicator(IndicatorBase):
    """현금 창출 능력 지표 (영업활동현금흐름 vs 당기순이익)"""

    operating_cash_flow: float  # 영업활동 현금흐름
    net_income: float  # 당기순이익
    is_cash_flow_greater: bool  # 영업활동현금흐름 > 당기순이익
    consecutive_warning_years: int = 0  # 연속 경고 연수


class InterestCoverageIndicator(IndicatorBase):
    """이자보상배율 지표"""

    operating_income: float  # 영업이익
    interest_expense: float  # 이자비용
    ratio: float  # 이자보상배율


class OperatingProfitGrowthIndicator(IndicatorBase):
    """영업이익 성장률 지표"""

    current_operating_income: float  # 당기 영업이익
    previous_operating_income: float  # 전기 영업이익
    growth_rate: float  # 성장률 (%)


class DilutionRiskIndicator(IndicatorBase):
    """희석 가능 물량 비율 지표"""

    convertible_shares: int  # 전환 가능 주식수
    total_shares: int  # 총 발행 주식수
    dilution_ratio: float  # 희석 비율 (%)


class InsiderTradingIndicator(IndicatorBase):
    """임원/주요주주 순매수 강도 지표"""

    net_buy_count: int  # 순매수 건수
    net_buy_executives: list[str]  # 순매수 임원 목록
    net_sell_count: int  # 순매도 건수
    ceo_bought: bool  # CEO 매수 여부


class ComprehensiveAnalysis(BaseModel):
    """종합 분석 결과"""

    corp_code: str
    corp_name: str
    analysis_date: str
    bsns_year: str

    # 5대 지표
    cash_generation: CashGenerationIndicator | None = None
    interest_coverage: InterestCoverageIndicator | None = None
    operating_profit_growth: OperatingProfitGrowthIndicator | None = None
    dilution_risk: DilutionRiskIndicator | None = None
    insider_trading: InsiderTradingIndicator | None = None

    # 종합 점수 및 신호
    overall_score: float  # 0-100
    overall_signal: SignalType
    recommendation: str
