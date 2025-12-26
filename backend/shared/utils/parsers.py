"""데이터 파싱 유틸리티"""

from datetime import datetime
import re


def parse_amount(value: str | None) -> float:
    """금액 문자열을 float로 변환

    예: "12,345,678,000" -> 12345678000.0
        "-1,234,567" -> -1234567.0
        "" or "-" -> 0.0
    """
    if not value or value.strip() in ("", "-", "－"):
        return 0.0

    # 쉼표 제거 및 공백 제거
    cleaned = value.replace(",", "").replace(" ", "").strip()

    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def parse_int(value: str | None) -> int:
    """정수 문자열을 int로 변환"""
    if not value or value.strip() in ("", "-", "－"):
        return 0

    cleaned = value.replace(",", "").replace(" ", "").strip()

    try:
        return int(float(cleaned))
    except ValueError:
        return 0


def parse_float(value: str | None) -> float:
    """실수 문자열을 float로 변환"""
    if not value or value.strip() in ("", "-", "－"):
        return 0.0

    cleaned = value.replace(",", "").replace(" ", "").replace("%", "").strip()

    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def parse_date(value: str | None) -> datetime | None:
    """날짜 문자열을 datetime으로 변환

    지원 형식:
    - "2024-01-01"
    - "2024년 01월 01일"
    - "20240101"
    """
    if not value or value.strip() in ("", "-"):
        return None

    formats = [
        "%Y-%m-%d",
        "%Y년 %m월 %d일",
        "%Y%m%d",
    ]

    cleaned = value.strip()

    for fmt in formats:
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue

    return None
