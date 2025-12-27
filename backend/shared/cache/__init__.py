"""Cache 모듈 - CSV Storage 어댑터

SQLite에서 CSV로 마이그레이션하면서 하위 호환성 유지
"""

from shared.storage.csv_storage import csv_storage


# ==========================================
# API 데이터 저장/조회 (DART Client용)
# ==========================================

def get_stored(endpoint: str, params: dict):
    """API 응답 조회 (CSV Storage 어댑터)"""
    return csv_storage.get_api_data(endpoint, params)


def store_data(endpoint: str, params: dict, response: dict):
    """API 응답 저장 (CSV Storage 어댑터)"""
    csv_storage.store_api_data(endpoint, params, response)


# ==========================================
# 분석 결과 저장/조회 (Router용)
# ==========================================

def save_buffett_analysis(
    corp_code: str,
    corp_name: str,
    stock_code: str,
    sector: str,
    bsns_year: str,
    fs_div: str,
    total_score: float,
    signal: str,
    filter_passed: bool,
    filter_reasons: list,
    indicators: dict,
    data_source: str,
):
    """분석 결과 저장 (CSV Storage 어댑터)"""
    csv_storage.save_analysis_result(
        corp_code=corp_code,
        corp_name=corp_name,
        stock_code=stock_code,
        sector=sector,
        bsns_year=bsns_year,
        fs_div=fs_div,
        total_score=total_score,
        signal=signal,
        filter_passed=filter_passed,
        filter_reasons=filter_reasons,
        indicators=indicators,
        data_source=data_source,
    )


def get_buffett_analysis(year: str, fs_div: str):
    """분석 결과 조회 (CSV Storage 어댑터)"""
    return csv_storage.get_analysis_results(year, fs_div)


def get_buffett_analysis_count(year: str, fs_div: str) -> int:
    """분석 결과 개수 조회 (CSV Storage 어댑터)"""
    return csv_storage.get_buffett_analysis_count(year, fs_div)


def clear_buffett_analysis(year: str = None, fs_div: str = None):
    """분석 결과 삭제 (CSV Storage 어댑터)"""
    csv_storage.clear_analysis_results(year, fs_div)


def get_available_years():
    """분석 가능한 년도 목록 (CSV Storage 어댑터)"""
    return csv_storage.get_available_years()


# ==========================================
# 하위 호환성 함수 (사용하지 않지만 import 에러 방지)
# ==========================================

def get_cache_stats():
    """캐시 통계 (CSV는 통계 미지원)"""
    return {"message": "CSV storage does not support stats"}


def get_stored_companies():
    """저장된 기업 목록 (CSV는 미지원)"""
    return []


def cleanup_expired():
    """만료된 캐시 정리 (CSV는 만료 개념 없음)"""
    pass


def get_cached(key: str):
    """캐시 조회 (CSV는 미지원)"""
    return None


def set_cached(key: str, value: any, ttl: int = None):
    """캐시 저장 (CSV는 미지원)"""
    pass


__all__ = [
    "get_stored",
    "store_data",
    "get_cache_stats",
    "get_stored_companies",
    "cleanup_expired",
    "get_cached",
    "set_cached",
    "get_buffett_analysis",
    "clear_buffett_analysis",
    "save_buffett_analysis",
    "get_buffett_analysis_count",
    "get_available_years",
]
