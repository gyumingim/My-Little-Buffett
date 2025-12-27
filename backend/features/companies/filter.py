"""기업 데이터 1단계 필터링 - 쓰레기 분리수거

Gemini 조언에 따른 정적 필터링: 분석 가치가 없는 잡주 제거
"""


def is_trash_stock(corp_name: str, stock_code: str) -> tuple[bool, str]:
    """
    1단계: 쓰레기 데이터 분리수거

    Returns:
        (is_trash, reason): 쓰레기 주식이면 (True, 사유), 아니면 (False, "")
    """
    # 1. 스팩(SPAC) 제거
    spac_keywords = ["스팩", "SPAC", "제1호", "제2호", "제3호", "제4호", "제5호",
                     "제6호", "제7호", "제8호", "제9호", "호스팩"]
    for keyword in spac_keywords:
        if keyword in corp_name:
            return True, f"스팩({keyword})"

    # 2. 우선주 제거 (종목코드 끝자리가 0이 아닌 것)
    if stock_code and len(stock_code) == 6:
        if stock_code[-1] != '0':
            return True, "우선주"

    # 3. 비상장사 제거 (종목코드가 없거나 6자리가 아닌 경우)
    if not stock_code or stock_code == "N/A" or len(stock_code) != 6:
        return True, "비상장"

    # 4. 특수목적법인 제거
    spv_keywords = ["투자회사", "리츠", "선박투자", "부동산투자", "인프라"]
    for keyword in spv_keywords:
        if keyword in corp_name:
            return True, f"특수목적법인({keyword})"

    # 5. 정리매매/관리종목 키워드
    risk_keywords = ["정리매매", "관리종목"]
    for keyword in risk_keywords:
        if keyword in corp_name:
            return True, f"리스크({keyword})"

    return False, ""


def calculate_market_cap_billion(stock_price: float, shares: int) -> float:
    """
    시가총액 계산 (단위: 억원)

    Args:
        stock_price: 주가 (원)
        shares: 발행주식수

    Returns:
        시가총액 (억원)
    """
    if stock_price <= 0 or shares <= 0:
        return 0

    return (stock_price * shares) / 100_000_000


def is_micro_cap(market_cap_billion: float, threshold: float = 500) -> bool:
    """
    마이크로캡 종목 여부 (기본값: 시가총액 500억 이하)

    재무제표 왜곡이 심한 소형주를 제거합니다.
    """
    return 0 < market_cap_billion < threshold
