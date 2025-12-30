"""
Utility functions for data loading and safe value extraction
"""
import json
from pathlib import Path
from typing import Any, Optional


def get_safe_value(data_dict: dict, key: str, default: Any = 0) -> Any:
    """
    JSON에서 값을 가져오되, 없거나 '-' 이면 기본값 반환

    Args:
        data_dict: 데이터 딕셔너리
        key: 키
        default: 기본값

    Returns:
        값 또는 기본값
    """
    value = data_dict.get(key, default)

    if value in ["-", "", None]:
        return default

    # 숫자 변환 시도
    if isinstance(default, (int, float)):
        try:
            # 쉼표 제거 후 변환
            if isinstance(value, str):
                value = value.replace(",", "")
            return float(value)
        except (ValueError, TypeError):
            return default

    return value


def load_json_safe(file_path: Path) -> Optional[dict]:
    """
    JSON 파일을 안전하게 로드

    Args:
        file_path: 파일 경로

    Returns:
        JSON 데이터 또는 None
    """
    try:
        if not file_path.exists():
            return None

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # DART API 응답 형식 처리
        if isinstance(data, dict) and 'list' in data:
            return data

        return data
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return None


def get_financial_data(corp_code: str, data_path: Path, year: str = "2024"):
    """
    재무제표 데이터 로드 (CFS 우선, 없으면 OFS)

    Args:
        corp_code: 기업 코드
        data_path: 데이터 경로
        year: 연도

    Returns:
        (data, source_type) 튜플. source_type은 "CFS", "OFS", "NONE" 중 하나
    """
    # 1순위: CFS (연결재무제표)
    cfs_path = data_path / "CFS" / year / f"{corp_code}.json"
    cfs_data = load_json_safe(cfs_path)

    if cfs_data and cfs_data.get('list'):
        return cfs_data, "CFS"

    # 2순위: OFS (개별재무제표)
    ofs_path = data_path / "OFS" / year / f"{corp_code}.json"
    ofs_data = load_json_safe(ofs_path)

    if ofs_data and ofs_data.get('list'):
        return ofs_data, "OFS"

    # 데이터 없음
    return None, "NONE"


def parse_amount(amount_str: str) -> float:
    """
    금액 문자열을 숫자로 변환 (쉼표 제거, 단위 고려)

    Args:
        amount_str: 금액 문자열

    Returns:
        숫자 값
    """
    if not amount_str or amount_str in ["-", ""]:
        return 0.0

    try:
        # 쉼표 제거
        clean_str = amount_str.replace(",", "").strip()

        # 단위 처리 (억, 만 등)
        if "억" in clean_str:
            number = float(clean_str.replace("억", ""))
            return number * 100000000
        elif "만" in clean_str:
            number = float(clean_str.replace("만", ""))
            return number * 10000
        else:
            return float(clean_str)
    except (ValueError, AttributeError):
        return 0.0
